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
from asyncio import Queue, Task, create_task, sleep
from enum import Enum, auto
from time import perf_counter_ns
from typing import Optional

from chess import Board, Move

from liboard import Bitboard


class MoveRecognizer:
    """Handles move recognition."""

    def __init__(self, bitboard_q: Queue, recognized_move_q: Queue, move_delay: float = 0.2):
        """
        Initialize a new MoveRecognizer.

        :param bitboard_q: Queue to get bitboards from the PhysicalBoard from.
        :param recognized_move_q: Queue to put recognized moves in.
        :param move_delay: delay before recognizing a move in ms
        """
        # general properties
        self._bitboard_q: Queue = bitboard_q
        self._recognized_move_q: Queue = recognized_move_q
        self._move_delay: float = move_delay

        # used for move recognition
        self._vboard: Board = Board()
        self._bitboard: Bitboard = Bitboard()
        self._lifted: set = set()
        self._task: Optional[Task] = None

    async def watch_bitboards(self):
        """Watch for incoming bitboards."""
        while True:
            self._on_new_bitboard(await self._bitboard_q.get())

    def _on_new_bitboard(self, bitboard: Bitboard):
        """Handle a received bitboard."""
        self._bitboard = bitboard
        if self._bitboard == Bitboard():
            self._start_game()
        else:
            self._lifted.update(Bitboard(self._vboard).occupied - self._bitboard.occupied)
            self._schedule_move_check()

    def _start_game(self):
        """Do what's necessary when a new game is started."""
        self._vboard.reset()
        self._lifted.clear()
        self._recognized_move_q.put_nowait(self._vboard.copy())

    def _candidate_move(self, move_type: str, from_set: set[int], to_set: set[int]):
        """
        Find the first move matching the supplied criteria.

        :param move_type: The type the move should be.
        :param from_set: A set of allowed departure squares.
        :param to_set: A set of allowed arrival squares.
        :return: The first legal move matching the criteria. None if no move matches.
        """
        for from_square in from_set:
            for to_square in to_set:
                try:
                    m = self._vboard.find_move(from_square, to_square)
                    if self._check_move_type(move_type, m):
                        return m
                except ValueError:
                    pass
        return None

    def _find_matching_move(self, disappearances: set[int], appearances: set[int],
                            tmp_lifted: set[int]) -> Optional[Move]:
        """
        Find the first move matching the supplied change in occupied squares.

        :param disappearances: All formerly occupied squares that are unoccupied now.
        :param appearances: All formerly unoccupied squares that are unoccupied now.
        :param tmp_lifted: All squares that are occupied in _vboard and _bitboard,
            but were unoccupied at some point since the last move.
        :return: The first move matching the data change or None if no move matches.
        """
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
        """Push a move, clear _lifted and call _callback."""
        self._lifted.clear()
        self._vboard.push(move)
        self._recognized_move_q.put_nowait(self._vboard.copy())

    async def _check_for_move(self, disappearances: set[int], appearances: set[int],
                              tmp_lifted: set[int]):
        """Wait for _move_delay and then check if there's a matching move."""
        await sleep(self._move_delay)
        if move := self._find_matching_move(disappearances, appearances, tmp_lifted):
            self._make_move(move)

    def _schedule_move_check(self):
        """Cancel the current task and call _check_for_move."""
        if self._task:
            self._task.cancel()
        disappearances = Bitboard(self._vboard).occupied - self._bitboard.occupied
        appearances = self._bitboard.occupied - Bitboard(self._vboard).occupied
        tmp_lifted = self._lifted & self._bitboard.occupied
        self._task = create_task(self._check_for_move(disappearances, appearances, tmp_lifted))

    def _check_move_type(self, move_type: str, move: Move):
        """Check whether m is of the given move_type."""
        if move_type == 'normal':
            return not (self._vboard.is_capture(move) or self._vboard.is_castling(move))
        elif move_type == 'capture':
            return self._vboard.is_capture(move) and not self._vboard.is_en_passant(move)
        elif move_type == 'en-passant':
            return self._vboard.is_en_passant(move)
        elif move_type == 'castling':
            return self._vboard.is_castling(move)


class BoardAPIMoveRecognizer(MoveRecognizer):
    """Handles move recognition when using the Board API."""

    def __init__(self, bitboard_q: Queue, recognized_move_q: Queue, streamed_move_q: Queue,
                 move_delay: float = 0.2):
        """
        Initialize a new BoardApiMoveRecognizer.

        :param bitboard_q: Queue to get bitboards from the PhysicalBoard from.
        :param recognized_move_q: Queue to put recognized moves in.
        :param streamed_move_q: Queue to get streamed moves from.
        :param move_delay: delay before recognizing a move in ms
        """
        super().__init__(bitboard_q, recognized_move_q, move_delay)
        self._streamed_move_q: Queue = streamed_move_q
        self._phase: Phase = Phase.CATCH_UP

    @property
    def phase(self):
        """Return the current phase."""
        return self._phase

    @phase.setter
    def phase(self, phase):
        self._phase = phase
        logging.info(f'Phase {phase}')

    async def watch_streamed_moves(self):
        """Watch for streamed moves."""
        while True:
            self._handle_streamed_moves(await self._streamed_move_q.get())

    def _handle_streamed_moves(self, moves: str):
        """Handle moves streamed from the board API."""
        logging.debug(f'Streamed moves: {moves}')
        self._vboard.reset()
        self._lifted.clear()
        for uci in moves.split():
            self._vboard.push_uci(uci)
        if self._bitboard != self._vboard:
            self.phase = Phase.CATCH_UP

    def _on_new_bitboard(self, bitboard: Bitboard):
        """Handle a received bitboard."""
        logging.debug(f'Bitboard:\n{bitboard}')
        self._bitboard = bitboard
        self._bb_timestamp = perf_counter_ns()
        if self.phase == Phase.CATCH_UP and self._bitboard == self._vboard:
            self.phase = Phase.RECOGNIZE
        elif self.phase == Phase.RECOGNIZE:
            self._lifted.update(Bitboard(self._vboard).occupied - self._bitboard.occupied)
            self._schedule_move_check()

    def _start_game(self):
        """
        Do what's necessary when a new game is started.

        For a BoardAPIMoveRecognizer, nothing should be done.
        """
        pass


class Phase(Enum):
    """Phases of move recognition."""

    RECOGNIZE = auto()
    CATCH_UP = auto()
