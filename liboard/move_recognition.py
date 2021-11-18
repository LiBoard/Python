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

"""LiBoard submodule for recognizing moves."""

from time import perf_counter_ns
from typing import Callable, Optional, Union

from chess import Board, Move

from liboard import Bitboard


class MoveRecognizer:
    """Handles move recognition for both sides."""

    def __init__(self, callback: Callable, move_delay: int = 0):
        """
        Initialize a new MoveRecognizer.

        :param callback: a callback for new games and moves
        :param move_delay: delay before recognizing a move in ms
        """
        self._vboard: Board = Board()
        self._bitboard: Bitboard = Bitboard()
        self._lifted: set = set()
        self._bb_timestamp: int = perf_counter_ns()
        self._move_delay: int = move_delay
        self._callback: Callable = callback
        self._move_types = {
            'normal': lambda m: not (self._vboard.is_capture(m) or self._vboard.is_castling(m)),
            'capture': lambda m: self._vboard.is_capture(m) and not self._vboard.is_en_passant(m),
            'en-passant': lambda m: self._vboard.is_en_passant(m),
            'castling': lambda m: self._vboard.is_castling(m)
        }

    def tick(self):
        """Check whether it's time to try generating a move."""
        if self._bitboard != Bitboard(self._vboard) and perf_counter_ns() >= (
                self._bb_timestamp + self._move_delay * 10 ** 6):
            disappearances = Bitboard(self._vboard).occupied - self._bitboard.occupied
            appearances = self._bitboard.occupied - Bitboard(self._vboard).occupied
            tmp_lifted = self._lifted & self._bitboard.occupied
            move = self._find_move(disappearances, appearances, tmp_lifted)
            if move:
                self._lifted.clear()
                self._vboard.push(move)
                self._callback(self._vboard)

    def on_event(self, event: Union[str, Bitboard]):
        """Handle events related to the PhysicalBoard."""
        if isinstance(event, str):
            pass
        elif isinstance(event, Bitboard):
            self._on_new_bitboard(event)

    def _on_new_bitboard(self, bitboard: Bitboard):
        self._bitboard = bitboard
        self._bb_timestamp = perf_counter_ns()
        if self._bitboard == Bitboard():
            self._start_game()
        else:
            self._lifted.update(Bitboard(self._vboard).occupied - self._bitboard.occupied)

    def _start_game(self):
        """Start a new game."""
        self._vboard.reset()
        self._lifted.clear()
        self._callback(self._vboard.copy())

    def _candidate_move(self, move_type: str, from_set: set[int], to_set: set[int]):
        for from_square in from_set:
            for to_square in to_set:
                try:
                    m = self._vboard.find_move(from_square, to_square)
                    if self._move_types[move_type](m):
                        return m
                except ValueError:
                    pass
        return None

    def _find_move(self, disappearances: set[int], appearances: set[int],
                   tmp_lifted: set[int]) -> Optional[Move]:
        self._bb_timestamp += 10 ** 10
        # TODO underpromotions
        if len(disappearances) == 1:
            if len(appearances) == 1:
                return self._candidate_move('normal', disappearances, appearances)
            elif not appearances and tmp_lifted:
                return self._candidate_move('capture', disappearances, tmp_lifted)
        elif len(disappearances) == 2:
            if len(appearances) == 1:
                return self._candidate_move('en-passant', disappearances, appearances)
            elif len(appearances) == 2:
                return self._candidate_move('castling', disappearances, appearances)
