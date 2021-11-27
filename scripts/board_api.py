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
import logging
from asyncio import gather, run, sleep

from liboard import ARGUMENT_PARSER
from liboard.lichess import APIConnection, EventPasser
from liboard.move_recognition import BoardAPIMoveRecognizer
from liboard.physical import USBBoard


def _init_logging(args):
    if args.debug.lower() in {'info', 'i'}:
        logging.basicConfig(level=logging.INFO)
    elif args.debug.lower() in {'debug', 'd'}:
        logging.basicConfig(level=logging.DEBUG)


async def _tick(*args, delay=0):
    while True:
        for a in args:
            a.tick()
        await sleep(delay)


async def _main(args: argparse.Namespace):
    _init_logging(args)
    passer = EventPasser()
    recognizer = BoardAPIMoveRecognizer(passer.pass_to_api, move_delay=args.move_delay)
    board = USBBoard(recognizer.on_event, port=args.port, baud_rate=args.baud_rate)
    with board.connection():
        async with APIConnection(args.token, passer.pass_to_recognizer) as connection:
            passer.recognizer, passer.connection = recognizer, connection
            await gather(_tick(board, delay=args.move_delay / 5), connection.loop())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[ARGUMENT_PARSER])
    parser.add_argument('-t', '--token', type=str, help='Personal Access Token')
    parser.add_argument('-D', '--debug', type=str, default='info', help='Debug mode')
    try:
        run(_main(parser.parse_args()))
    except KeyboardInterrupt:
        pass
