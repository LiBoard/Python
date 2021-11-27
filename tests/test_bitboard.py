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

from collections.abc import Iterable
from typing import Any

import chess
import pytest
from bitstring import Bits

from liboard import Bitboard


@pytest.mark.parametrize(('test_input', 'expected'), [
    (Bits(hex='FFFF00000000FFFF'), {i for i in range(64) if i < 16 or i >= 48})
])
def test_constructor_bits(test_input: Bits, expected: set):
    occupied = Bitboard(test_input).occupied
    assert isinstance(occupied, frozenset)
    assert occupied == expected


@pytest.mark.parametrize(('test_input', 'expected'), [
    (chess.Board(), {i for i in range(64) if i < 16 or i >= 48})
])
def test_constructor_board(test_input: chess.Board, expected: set):
    occupied = Bitboard(test_input).occupied
    assert isinstance(occupied, frozenset)
    assert occupied == expected


def test_constructor_invalid():
    with pytest.raises(TypeError):
        Bitboard(Bits(hex='FFFF00000000FFFF').int)


@pytest.mark.parametrize(('bitboard', 'other', 'expected'), [
    (Bitboard(Bits(hex='FFFF00000000FFFF')), Bits(hex='FFFF00000000FFFF'), True),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), chess.Board(), True),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), {i for i in range(64) if i < 16 or i >= 48}, True),
    (Bitboard(Bits(hex='FFFF00000000FFFF')),
     frozenset({i for i in range(64) if i < 16 or i >= 48}),
     True),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), Bitboard(chess.Board()), True),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), Bits(hex='FFFF00001000FFEF'), False),
    (Bitboard(Bits(hex='FFFF00000000FFFF')),
     chess.Board('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1'), False),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), {i for i in range(16)}, False),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), Bitboard(Bits(hex='FFFF00001000FFEF')), False),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), Bits(hex='FFFF00000000FFFF').int, False)
])
def test_equals(bitboard: Bitboard, other: Any, expected: bool):
    assert (bitboard == other) is expected


@pytest.mark.parametrize(('bitboard', 'item'), [
    (Bitboard(Bits(hex='FFFF00000000FFFF')), 0),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), {i for i in range(64) if i < 16 or i >= 48}),
])
def test_in(bitboard: Bitboard, item):
    if isinstance(item, Iterable):
        assert item not in bitboard
        for i in item:
            assert i in bitboard
    else:
        assert item in bitboard


@pytest.mark.parametrize(('bitboard', 'item'), [
    (Bitboard(Bits(hex='FFFF00000000FFFF')), 16),
    (Bitboard(Bits(hex='FFFF00000000FFFF')), {i for i in range(16, 48)}),
])
def test_not_in(bitboard: Bitboard, item):
    if isinstance(item, Iterable):
        assert item not in bitboard
        for i in item:
            assert i not in bitboard
    else:
        assert item not in bitboard
