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
from asyncio import Queue, gather, run
from traceback import print_exc

from chess.pgn import Game

from liboard import ARGUMENT_PARSER
from liboard.move_recognition import MoveRecognizer
from liboard.physical import USBBoard


async def _watch_recognized_moves(recognized_move_q: Queue, _game: Game, stdscreen: curses.window):
    node = _game
    while True:
        board = await recognized_move_q.get()
        stdscreen.clear()
        if not board.ply():
            node = _game
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


async def _coro(stdscreen: curses.window, _game: Game, _args: argparse.Namespace):
    curses.curs_set(False)
    curses.use_default_colors()
    stdscreen.clear()
    stdscreen.addstr('Ready to start.')
    stdscreen.refresh()
    bitboard_q, move_q = Queue(), Queue()
    board = USBBoard(bitboard_q, port=args.port, baud_rate=args.baud_rate)
    recognizer = MoveRecognizer(bitboard_q, move_q, move_delay=args.move_delay)
    await gather(
        board.watch_incoming(),
        recognizer.watch_bitboards(),
        _watch_recognized_moves(move_q, game, stdscreen)
    )


def _main(stdscreen: curses.window, _game: Game, _args: argparse.Namespace):
    run(_coro(stdscreen, _game, _args))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[ARGUMENT_PARSER])
    parser.add_argument('-o', '--output-file', default='',
                        help='Optional file to write the pgn to')
    args = parser.parse_args()
    game = Game()
    game.headers['Date'] = datetime.datetime.now().strftime('%Y.%m.%d')
    try:
        curses.wrapper(_main, game, args)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print_exc(e)
    finally:
        print(game)
        if args.output_file:
            with open(args.output_file, 'a') as of:
                of.write(str(game))
