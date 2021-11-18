#! /usr/bin/python3

"""Simulate keyboard inputs for the moves by one side."""

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

import chess
import chess.pgn
import pyautogui

import liboard
from liboard import LiBoard


def _main(_args: argparse.Namespace):
    board = LiBoard(_args.port, _args.baud_rate, _args.move_delay)

    @board.start_handler
    def print_start(_board: LiBoard) -> bool:
        print("New game.")
        return False

    @board.move_handler
    def print_move(_board: LiBoard, _move: chess.Move) -> bool:
        print(_move)
        if bool(_board.chessboard.ply() % 2) != args.side:
            pyautogui.write(str(_move))
        return False

    while True:
        board.update()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[liboard.ARGUMENT_PARSER])
    parser.add_argument('-B', '--black', action='store_const', dest='side', default=0, const=1,
                        help='Play as black')
    args = parser.parse_args()
    try:
        _main(args)
    except KeyboardInterrupt:
        pass
