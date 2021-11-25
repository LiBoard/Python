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

import logging
from asyncio import Task, create_task, sleep
from enum import Enum, auto
from time import perf_counter_ns
from typing import Callable, Optional, Union

from chess import Board, Move

from liboard import Bitboard


class MoveRecognizer:
    """Handles move recognition."""

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
        self._task: Optional[Task] = None

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
            self._schedule_move_check()

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

    def _make_move(self, move: Move):
        self._lifted.clear()
        self._vboard.push(move)
        self._callback(self._vboard)

    async def _check_for_move(self, disappearances: set[int], appearances: set[int],
                              tmp_lifted: set[int]):
        await sleep(self._move_delay)
        if move := self._find_move(disappearances, appearances, tmp_lifted):
            self._make_move(move)

    def _schedule_move_check(self):
        if self._task:
            self._task.cancel()
        disappearances = Bitboard(self._vboard).occupied - self._bitboard.occupied
        appearances = self._bitboard.occupied - Bitboard(self._vboard).occupied
        tmp_lifted = self._lifted & self._bitboard.occupied
        self._task = create_task(self._check_for_move(disappearances, appearances, tmp_lifted))


class BoardAPIMoveRecognizer(MoveRecognizer):
    """Handles move recognition when using the Board API."""

    def __init__(self, callback: Callable, move_delay: int = 0):
        """
        Initialize a new BoardApiMoveRecognizer.

        :param callback: a callback for new games and moves
        :param move_delay: delay before recognizing a move in ms
        """
        super().__init__(callback, move_delay)
        self._phase: Phase = Phase.CATCH_UP

    @property
    def phase(self):
        """Return the current phase."""
        return self._phase

    @phase.setter
    def phase(self, phase):
        self._phase = phase
        logging.info(f'Phase {phase}')

    def handle_streamed_moves(self, moves: str):
        """Handle moves streamed from the board API."""
        logging.debug(f'Streamed moves: {moves}')

        self._vboard.reset()
        self._lifted.clear()
        for uci in moves.split():
            self._vboard.push_uci(uci)
        if self._bitboard != self._vboard:
            self.phase = Phase.CATCH_UP

    def _on_new_bitboard(self, bitboard: Bitboard):
        logging.debug(f'Bitboard:\n{bitboard}')
        self._bitboard = bitboard
        self._bb_timestamp = perf_counter_ns()
        if self.phase == Phase.CATCH_UP and self._bitboard == self._vboard:
            self.phase = Phase.RECOGNIZE
        elif self.phase == Phase.RECOGNIZE:
            self._lifted.update(Bitboard(self._vboard).occupied - self._bitboard.occupied)
            self._schedule_move_check()

    def _start_game(self):
        # BoardAPIMoveRecognizer should ignore game starts
        pass


class Phase(Enum):
    """Phases of move recognition."""

    RECOGNIZE = auto()
    CATCH_UP = auto()
