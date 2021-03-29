# Copyright (C) 2021  Philipp Leclercq
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import chess
from serial import Serial
from bitstring import Bits
from time import time_ns
from typing import Callable, Optional


# TODO documentation

class LiBoard:
    MOVE_DELAY = 0  # in ns
    STARTING_POSITION = Bits(hex="C3C3C3C3C3C3C3C3")

    def __init__(self, port="/dev/ttyACM0", baud_rate=9600):
        self._serial = Serial(port, baudrate=baud_rate)
        self.chessboard: chess.Board = chess.Board()

        self._start_handler: Callable[[LiBoard], bool] = None
        self._move_handler: Callable[[LiBoard, chess.Move], bool] = None

        # data corresponding to the position of self.chessboard
        self._known_position_data: Bits = LiBoard.STARTING_POSITION
        # data incoming from the board
        self._physical_position_data = self._known_position_data
        self._last_change = time_ns()  # last time the physical position changed
        # has _generate_move() been called with the current _physical_position_data?
        self._pos_checked = False
        self._lifted_pieces = set()

    def __del__(self):
        del self._serial

    @staticmethod
    def _is_starting_position(bits: Bits) -> bool:
        return bits == LiBoard.STARTING_POSITION

    @staticmethod
    def _get_occupied_squares(bits: Bits) -> set[int]:
        occupied_squares = set()
        # The bits in the incoming data have a different order than the squares in python-chess,
        # making this conversion loop necessary
        # TODO change arduino bit order to python-chess square order
        for arduino_index in set(bits.findall("0b1")):
            file = 7 - int(arduino_index / 8)
            rank = 7 - (arduino_index % 8)
            occupied_squares.add((rank * 8) + file)
        return occupied_squares

    def start_handler(self, handler: Callable[['LiBoard'], bool]):
        self._start_handler = handler
        return handler

    def move_handler(self, handler: Callable[['LiBoard', chess.Move], bool]):
        self._move_handler = handler
        return handler

    def start_game(self):
        self.chessboard.reset()
        self._known_position_data = LiBoard.STARTING_POSITION
        self._lifted_pieces = set()
        if self._start_handler is not None:
            self._start_handler()

    def _get_board_data(self):
        if self._serial.in_waiting >= 8:
            self._physical_position_data = Bits(self._serial.read(8))
            if LiBoard._is_starting_position(self._physical_position_data):
                self.start_game()
                return
            self._pos_checked = False
            self._last_change = time_ns()
            self._lifted_pieces.update(LiBoard._get_occupied_squares(self._known_position_data).difference(
                LiBoard._get_occupied_squares(self._physical_position_data)))

    def _generate_move(self) -> bool:
        self._pos_checked = True

        # get the indices of the occupied squares
        current_position_occupied_squares = LiBoard._get_occupied_squares(
            self._known_position_data)
        occupied_squares = LiBoard._get_occupied_squares(
            self._physical_position_data)

        # get the differences between the occupied squares in the last known and the physical position
        disappearances = current_position_occupied_squares.difference(
            occupied_squares)
        appearances = occupied_squares.difference(
            current_position_occupied_squares)
        temporarily_lifted_pieces = self._lifted_pieces.intersection(
            occupied_squares)

        # TODO underpromotions
        if len(disappearances) == 1 and len(appearances) == 1:  # "normal" move
            move = self._find_candidate_move(disappearances.pop(), appearances.pop())
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
        return False

    def _find_candidate_move(self, from_square: int, to_square: int) -> Optional[chess.Move]:
        try:
            return self.chessboard.find_move(from_square, to_square)
        except ValueError:
            return None

    def _make_move(self, move: chess.Move) -> bool:
        # Usually, every move given as an argument should be legal, as it was returned by self.chessboard.find_move.
        # However, self.chessboard.push doesn't check for legality, so I'll leave this check as a safety measure.
        if move in self.chessboard.legal_moves:
            self._known_position_data = self._physical_position_data
            self._lifted_pieces = set()
            self.chessboard.push(move)
            if self._move_handler is not None:
                self._move_handler()
            return True
        return False

    def update(self):
        self._get_board_data()
        if self._physical_position_data != self._known_position_data and time_ns() >= (
                self._last_change + LiBoard.MOVE_DELAY) and not self._pos_checked:
            self._generate_move()
