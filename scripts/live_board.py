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
import sys

import chess
import chess.pgn

import liboard
from liboard import LiBoard

global game, node


def _main(stdscreen: curses.window, args: argparse.Namespace):
    board = LiBoard(args.port, args.baud_rate, args.move_delay)
    global game, node
    game = chess.pgn.Game()
    game.headers['Date'] = datetime.datetime.now().strftime('%Y.%m.%d')
    node = game

    curses.curs_set(False)
    curses.use_default_colors()

    stdscreen.clear()
    stdscreen.addstr('Ready to start.')
    stdscreen.refresh()

    @board.start_handler
    def print_start_message(_board: LiBoard) -> bool:
        global game, node
        node = game
        stdscreen.clear()
        stdscreen.addstr('New game.\n')
        stdscreen.addstr(str(_board.chessboard))
        stdscreen.refresh()
        return False

    @board.move_handler
    def print_move(_board: LiBoard, _move: chess.Move) -> bool:
        global node
        if any(variation.move == _move for variation in node.variations):
            node.promote_to_main(_move)
            node = node.next()
        else:
            node = node.add_main_variation(_move)
        stdscreen.clear()
        stdscreen.addstr(
            '{num}. {ellipsis}{san}\n'.format(num=int((node.ply() + 1) / 2),
                                              ellipsis=('' if node.ply() % 2 else '...'),
                                              san=node.san()))
        stdscreen.addstr(str(_board.chessboard))
        stdscreen.refresh()
        return False

    while True:
        board.update()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[liboard.ARGUMENT_PARSER])
    parser.add_argument('-o', '--output-file', default='',
                        help='Optional file to write the pgn to')
    args = parser.parse_args()

    exit_code = 0
    # noinspection PyBroadException
    try:
        curses.wrapper(_main, args)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e, file=sys.stderr)
        exit_code = 1
    finally:
        print(game)
        if args.output_file:
            with open(args.output_file, 'a') as of:
                of.write(str(game))
        sys.exit(exit_code)
