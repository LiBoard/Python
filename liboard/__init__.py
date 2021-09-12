"""
Interact with LiBoard-type electronic chessboards.

Classes:
    LiBoard
"""

#  LiBoard
#  Copyright (C) 2021 Philipp Leclercq
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 3 as published by
#  the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import argparse
from time import time_ns
from typing import Callable, Optional

import chess
from bitstring import Bits
from serial import Serial


def _arg_parser():
    """
    Creates an ArgumentParser that has common args for instantiating a LiBoard.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-p', '--port', default='/dev/ttyACM0',
                        help='The serial port which the board is connected to (Default /dev/ttyACM0)')
    parser.add_argument('-b', '--baud-rate', default=9600, type=int, help='The board\'s baud rate (Default 9600)')
    parser.add_argument('-d', '--move-delay', default=0, type=int,
                        help='The delay before a move is recognized (Default 0)')
    return parser


class _PhysicalPosition:
    def __init__(self, *args):
        if len(args) != 1:
            raise IndexError
        if type(args[0]) == Bits:
            self.bits = args[0]
        elif type(args[0]) == chess.Board:
            self.bits = Bits(uint=args[0].occupied, length=64)
        else:
            raise TypeError
        self.occupied_squares = {63 - i for i in self.bits.findall('0b1')}

    def __eq__(self, other):
        if type(other) == _PhysicalPosition:
            return other.bits == self.bits
        return super.__eq__(self, other)


_STARTING_POSITION = _PhysicalPosition(Bits(hex='FFFF00000000FFFF'))


class LiBoard:
    """Represents a LiBoard-type electronic chessboard."""

    def __init__(self, port, baud_rate, move_delay):
        """
        Constructs and initializes a LiBoard object.
        :param port: The serial port which the LiBoard is connected to.
        :param baud_rate: The baud rate used to communicate with the board.
        :param move_delay: The delay in ms before a move is recognized. Useful to enable "sliding" pieces.
        """
        self._serial = Serial(port, baudrate=baud_rate)
        self.chessboard: chess.Board = chess.Board()
        self._move_delay: int = move_delay

        self._start_handler: Optional[Callable[[LiBoard], bool]] = None
        self._move_handler: Optional[Callable[[LiBoard, chess.Move], bool]] = None

        self._physical_position = _STARTING_POSITION  # data incoming from the board
        self._last_change = time_ns()
        self._pos_checked = False
        self._lifted_pieces = set()

    def __del__(self):
        """Deletes the LiBoard object and closes the serial connection."""
        del self._serial

    def start_game(self):
        """Reset the chessboard to start a new game. Call the start handler."""
        self.chessboard.reset()
        self._lifted_pieces = set()
        if self._start_handler is not None:
            self._start_handler(self)

    def update(self):
        """
        Update the LiBoard by checking for new data and trying to make a
        new move if the data hasn't changed for self._move_delay nanoseconds.
        """
        self._get_board_data()
        if self._physical_position != _PhysicalPosition(self.chessboard.occupied) and \
                time_ns() >= (self._last_change + self._move_delay * (10 ** 6)) and not self._pos_checked:
            self._generate_move()

    def _get_board_data(self):
        """
        Get the data from the connected LiBoard.
        The new board data will be stored in self._physical_position.
        """
        if self._serial.in_waiting >= 8:
            self._physical_position = _PhysicalPosition(Bits(self._serial.read(8)))
            if self._physical_position == _STARTING_POSITION:
                return self.start_game()
            self._pos_checked = False
            self._last_change = time_ns()
            # Add all squares which were occupied after the last move but aren't now to _lifted_pieces.
            # This is necessary to be able to recognise captures.
            self._lifted_pieces.update(
                _PhysicalPosition(self.chessboard.occupied).occupied_squares.difference(
                    self._physical_position.occupied_squares))

    # region Handler decorators
    def start_handler(self, handler: Callable[['LiBoard'], bool]):
        """Set the handler for game starts."""
        self._start_handler = handler
        return handler

    def move_handler(self, handler: Callable[['LiBoard', chess.Move], bool]):
        """Set the handler for new moves."""
        self._move_handler = handler
        return handler

    # endregion

    # region Making moves out of raw data
    def _generate_move(self) -> bool:
        """
        Try to generate a move matching the data.
        :return: True if a legal move was found.
        """
        self._pos_checked = True

        # region Determinate delta between last known and physical position
        # Get the indices of the occupied squares in the current and the last known position.
        current_position_occupied_squares = _PhysicalPosition(
            Bits(uint=self.chessboard.occupied, length=64)).occupied_squares
        known_position_occupied_squares = self._physical_position.occupied_squares

        # Get the differences between the occupied squares in the current and the last known position.
        disappearances = current_position_occupied_squares.difference(
            known_position_occupied_squares)
        appearances = known_position_occupied_squares.difference(
            current_position_occupied_squares)
        # Get all squares that were vacated temporarily between the last move and now,
        # which is necessary to recognise captures.
        temporarily_lifted_pieces = self._lifted_pieces.intersection(
            known_position_occupied_squares)
        # endregion

        # TODO underpromotions
        # region Move type recognition
        if len(disappearances) == 1 and len(appearances) == 1:  # "normal" move
            move = self._find_candidate_move(
                disappearances.pop(), appearances.pop())
            return move and not self.chessboard.is_capture(move) and not \
                self.chessboard.is_castling(move) and self._make_move(move)
        elif len(disappearances) == 1 and not appearances and temporarily_lifted_pieces:  # "simple" capture
            from_square = disappearances.pop()
            for tlp in temporarily_lifted_pieces:
                move = self._find_candidate_move(from_square, tlp)
                if move and self.chessboard.is_capture(move) and self._make_move(move):
                    return True
        elif len(disappearances) == 2 and len(appearances) == 1:  # en passant
            to_square = appearances.pop()
            for from_square in disappearances:
                move = self._find_candidate_move(from_square, to_square)
                if move and self.chessboard.is_en_passant(move) and self._make_move(move):
                    return True
        elif len(disappearances) == 2 and len(appearances) == 2:  # castling
            for from_square in disappearances:
                for to_square in appearances:
                    move = self._find_candidate_move(from_square, to_square)
                    if move and self.chessboard.is_castling(move):
                        return self._make_move(move)
        # endregion
        return False

    def _find_candidate_move(self, from_square: int, to_square: int) -> Optional[chess.Move]:
        """
        Find a legal move from from_square to to_square.
        :param from_square: The starting square for the move.
        :param to_square: The target square for the move.
        :return: The Move if one was found. Otherwise return None.
        """
        try:
            return self.chessboard.find_move(from_square, to_square)
        except ValueError:
            return None

    def _make_move(self, move: chess.Move) -> bool:
        """
        Try to make the given move and call the move handler if successful.
        :param move: The move to make.
        :return: True if the move was made. False if the move was illegal.
        """
        # Usually, every move given as an argument should be legal, as it was returned by self.chessboard.find_move.
        # However, self.chessboard.push doesn't check for legality, so I'll leave this check as a safety measure.
        if move in self.chessboard.legal_moves:
            self._lifted_pieces = set()
            self.chessboard.push(move)
            if self._move_handler is not None:
                self._move_handler(self, move)
            return True
        return False

    # endregion


ARGUMENT_PARSER = _arg_parser()
