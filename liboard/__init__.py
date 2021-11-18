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

"""Interact with LiBoard-type electronic chessboards."""

import argparse
from collections.abc import Set
from typing import Any, Union

import chess
from bitstring import Bits

ARGUMENT_PARSER = argparse.ArgumentParser(add_help=False)
ARGUMENT_PARSER.add_argument('-p', '--port', default='/dev/ttyACM0',
                             help='The serial port which the board is connected to ' +
                                  '(Default /dev/ttyACM0)')
ARGUMENT_PARSER.add_argument('-b', '--baud-rate', default=9600, type=int,
                             help='The board\'s baud rate (Default 9600)')
ARGUMENT_PARSER.add_argument('-d', '--move-delay', default=0, type=int,
                             help='The delay before a move is recognized (Default 0)')


class Bitboard:
    """Bitboard representation of a chessboard."""

    def __init__(self, board: Union[Bits, chess.Board, bytes] = Bits(hex='FFFF00000000FFFF')):
        """
        Create a new Bitboard.

        :param board: bytes, Bits, or a chess.Board to construct the Bitboard from
        """
        if isinstance(board, Bits):
            self._bits: Bits = board
        elif isinstance(board, chess.Board):
            self._bits: Bits = Bits(uint=board.occupied, length=64)
        elif isinstance(board, bytes):
            self._bits: Bits = Bits(board)
        else:
            raise TypeError('board must be Bits|Board|bytes')
        self.occupied = frozenset((63-i for (i, v) in enumerate(self._bits) if v))

    @property
    def bits(self):
        """Return the bits of this bitboard."""
        return self._bits

    def __eq__(self, other: Any) -> bool:
        """Whether this Bitboard is equal to other."""
        if isinstance(other, Bitboard):
            return other.bits == self.bits
        elif isinstance(other, Bits):
            return other == self.bits
        elif isinstance(other, Set):
            return other == self.occupied
        elif isinstance(other, bytes):
            return Bits(other) == self.bits
        elif isinstance(other, chess.Board):
            return Bits(uint=other.occupied, length=64) == self.bits
        else:
            return False

    def __contains__(self, item: Any) -> bool:
        """Whether this Bitboard contains item."""
        if isinstance(item, int):
            return item in self.occupied
        else:
            return False
