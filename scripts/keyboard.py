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
from asyncio import Queue, gather, run

import pyautogui
from chess import BLACK, WHITE

from liboard import ARGUMENT_PARSER
from liboard.move_recognition import MoveRecognizer
from liboard.physical import USBBoard


async def _watch_recognized_moves(recognized_move_q, turn):
    while True:
        board = await recognized_move_q.get()
        if not board.ply():
            print('New game.')
        else:
            move = board.move_stack[-1]
            print(move)
            if board.turn != turn:
                pyautogui.write(str(move))


async def _main(args: argparse.Namespace):
    bitboard_q, recognized_move_q = Queue(), Queue()
    board = USBBoard(bitboard_q, port=args.port, baud_rate=args.baud_rate)
    recognizer = MoveRecognizer(bitboard_q, recognized_move_q, move_delay=args.move_delay)
    await gather(
        board.watch_incoming(),
        recognizer.watch_bitboards(),
        _watch_recognized_moves(recognized_move_q, args.turn)
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[ARGUMENT_PARSER])
    parser.add_argument('-B', '--black', action='store_const', dest='turn', default=WHITE,
                        const=BLACK, help='Play as black')
    try:
        run(_main(parser.parse_args()))
    except KeyboardInterrupt:
        pass
