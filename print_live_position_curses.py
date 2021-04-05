#! /usr/bin/python3

# Copyright (C) 2021  Philipp Leclercq
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Show the live position from the board using curses. Print the pgn on exit."""

import curses
import sys
import chess
import chess.pgn
import datetime
from liboard import LiBoard

global game, node


def main(stdscreen: curses.window):
    board = LiBoard()
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
    exit_code = 0
    # noinspection PyBroadException
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e, file=sys.stderr)
        exit_code = 1
    finally:
        print(game)
        sys.exit(exit_code)
