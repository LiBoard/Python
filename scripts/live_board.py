#! /usr/bin/python3

"""Show the live position from the board and print the pgn on exit."""

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
import curses
import datetime
from time import sleep

import chess.pgn
from chess import Board

from liboard import ARGUMENT_PARSER
from liboard.move_recognition import MoveRecognizer
from liboard.physical import USBBoard

global game, node


def _main(stdscreen: curses.window, _args: argparse.Namespace):
    curses.curs_set(False)
    curses.use_default_colors()

    global game, node
    game = chess.pgn.Game()
    game.headers['Date'] = datetime.datetime.now().strftime('%Y.%m.%d')
    node = game

    def _callback(board: Board):
        global game, node
        stdscreen.clear()
        if not board.ply():
            node = game
            stdscreen.addstr('New game.\n')
        else:
            move = board.move_stack[-1]
            if any(variation.move == move for variation in node.variations):
                node.promote_to_main(move)
                node = node.next()
            else:
                node = node.add_main_variation(move)
            stdscreen.addstr(
                '{num}. {ellipsis}{san}\n'.format(num=int((node.ply() + 1) / 2),
                                                  ellipsis=('' if node.ply() % 2 else '...'),
                                                  san=node.san()))
        stdscreen.addstr(str(board))
        stdscreen.refresh()

    recognizer = MoveRecognizer(_callback, _args.move_delay)
    usb_board = USBBoard(recognizer.on_event, _args.port, _args.baud_rate)

    stdscreen.clear()
    stdscreen.addstr('Ready to start.')
    stdscreen.refresh()
    with usb_board.connection():
        while True:
            usb_board.tick()
            recognizer.tick()
            sleep(_args.move_delay / 5000)  # helps reducing CPU load


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[ARGUMENT_PARSER])
    parser.add_argument('-o', '--output-file', default='',
                        help='Optional file to write the pgn to')
    args = parser.parse_args()
    try:
        curses.wrapper(_main, args)
    except KeyboardInterrupt:
        pass
    finally:
        print(game)
        if args.output_file:
            with open(args.output_file, 'a') as of:
                of.write(str(game))
