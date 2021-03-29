# Copyright (C) 2021  Philipp Leclercq
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
Interact with LiBoard-type electronic chessboards.

Classes:
    LiBoard
"""

import chess
from serial import Serial
from bitstring import Bits
from time import time_ns
from typing import Callable, Optional


class LiBoard:
    """Represents a LiBoard-type electronic chessboard."""
    MOVE_DELAY = 0  # in ns
    STARTING_POSITION = Bits(hex='C3C3C3C3C3C3C3C3')

    @staticmethod
    def _is_starting_position(bits: Bits) -> bool:
        """
        Check if a position equals the starting position.
        :param bits: The position to check.
        :return: True if the position is the starting position, False otherwise.
        """
        return bits == LiBoard.STARTING_POSITION

    @staticmethod
    def _get_occupied_squares(bits: Bits) -> set[int]:
        """
        Return a set of occupied squares in a position.
        :param bits: The position.
        :return: A set of ints with each int corresponding to an occupied square
            (see python-chess for the mapping of ints to squares).
        """
        occupied_squares = set()
        # The bits in the incoming data have a different order than the squares in python-chess,
        # making this conversion loop necessary.
        # Order of incoming data: H8, H7, ..., A2, A1.
        # Order of python-chess: A1, B1, ..., G8, H8.
        # TODO change arduino bit order to python-chess square order
        for arduino_index in set(bits.findall('0b1')):
            file = 7 - int(arduino_index / 8)
            rank = 7 - (arduino_index % 8)
            occupied_squares.add((rank * 8) + file)
        return occupied_squares

    def __init__(self, port='/dev/ttyACM0', baud_rate=9600):
        """
        Constructs and initializes a LiBoard object.
        :param port: The serial port which the LiBoard is connected to. Default: /dev/ttyACM0.
        :param baud_rate: The baud rate used to communicate with the board. Default: 9600.
        """
        self._serial = Serial(port, baudrate=baud_rate)
        self.chessboard: chess.Board = chess.Board()

        self._start_handler: Optional[Callable[[LiBoard], bool]] = None
        self._move_handler: Optional[Callable[[LiBoard, chess.Move], bool]] = None

        # data corresponding to the position of self.chessboard
        self._known_position_data: Bits = LiBoard.STARTING_POSITION
        # data incoming from the board
        self._physical_position_data = self._known_position_data
        self._last_change = time_ns()
        self._pos_checked = False
        self._lifted_pieces = set()

    def __del__(self):
        """Deletes the LiBoard object and closes the serial connection."""
        del self._serial

    def start_game(self):
        """Reset the chessboard to start a new game. Call the start handler."""
        self.chessboard.reset()
        self._known_position_data = LiBoard.STARTING_POSITION
        self._lifted_pieces = set()
        if self._start_handler is not None:
            self._start_handler(self)

    def update(self):
        """
        Update the LiBoard by checking for new data and trying to make a
        new move if the data hasn't changed forMOVE_DELAY nanoseconds.
        """
        self._get_board_data()
        if self._physical_position_data != self._known_position_data and \
                time_ns() >= (self._last_change + LiBoard.MOVE_DELAY) and not self._pos_checked:
            self._generate_move()

    def _get_board_data(self):
        """
        Get the data from the connected LiBoard.
        The new board data will be stored in self._physical_position_data.
        """
        if self._serial.in_waiting >= 8:
            self._physical_position_data = Bits(self._serial.read(8))
            if LiBoard._is_starting_position(self._physical_position_data):
                return self.start_game()
            self._pos_checked = False
            self._last_change = time_ns()
            # Add all squares which were occupied after the last move but aren't now to _lifted_pieces.
            # This is necessary to be able to recognise captures.
            self._lifted_pieces.update(LiBoard._get_occupied_squares(self._known_position_data).difference(
                LiBoard._get_occupied_squares(self._physical_position_data)))

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
        Try to generate a move leading from _known_position_data to _physical_position_data.
        :return: True if a legal move was found.
        """
        self._pos_checked = True

        # region Determinate delta between last known and physical position
        # Get the indices of the occupied squares in the current and the last known position.
        current_position_occupied_squares = LiBoard._get_occupied_squares(
            self._known_position_data)
        known_position_occupied_squares = LiBoard._get_occupied_squares(
            self._physical_position_data)

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
            self._known_position_data = self._physical_position_data
            self._lifted_pieces = set()
            self.chessboard.push(move)
            if self._move_handler is not None:
                self._move_handler(self, move)
            return True
        return False

    # endregion
