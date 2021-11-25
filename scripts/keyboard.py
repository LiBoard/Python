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
from time import sleep

import pyautogui
from chess import BLACK, WHITE

from liboard import ARGUMENT_PARSER
from liboard.move_recognition import MoveRecognizer
from liboard.physical import USBBoard


def _main(args: argparse.Namespace):
    def _callback(board):
        if not board.ply():
            print('New game.')
        else:
            move = board.move_stack[-1]
            print(move)
            if board.turn != args.turn:
                pyautogui.write(str(move))

    recognizer = MoveRecognizer(_callback, args.move_delay)
    usb_board = USBBoard(recognizer.on_event, args.port, args.baud_rate)

    with usb_board.connection():
        while True:
            usb_board.tick()
            sleep(args.move_delay / 5000)  # helps reducing CPU load


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[ARGUMENT_PARSER])
    parser.add_argument('-B', '--black', action='store_const', dest='turn', default=WHITE,
                        const=BLACK, help='Play as black')
    try:
        _main(parser.parse_args())
    except KeyboardInterrupt:
        pass
