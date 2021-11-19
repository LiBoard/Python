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
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import sleep

import requests
from chess import Board

from liboard import ARGUMENT_PARSER
from liboard.move_recognition import BoardApiMoveRecognizer
from liboard.physical import USBBoard


def _init_logging(args):
    if args.debug.lower() in {'info', 'i'}:
        logging.basicConfig(level=logging.INFO)
    elif args.debug.lower() in {'debug', 'd'}:
        logging.basicConfig(level=logging.DEBUG)


def _stream(url, headers):
    stream = requests.get(url, headers=headers, stream=True)
    if stream.encoding is None:
        stream.encoding = 'utf-8'
    yield from (json.loads(item) for item in stream.iter_lines(decode_unicode=True) if item)


def _watch_events(queue, headers):
    for _item in _stream('https://lichess.org/api/stream/event', headers):
        logging.debug(_item)
        queue.put(_item)


def _watch_moves(queue, headers, game_id):
    for _item in _stream(f'https://lichess.org/api/board/game/stream/{game_id}', headers):
        logging.debug(_item)
        state = _item if _item['type'] == 'gameState' \
            else _item['state'] if _item['type'] == 'gameFull' else None
        if state:
            if state['status'] != 'started':
                logging.info(f"Status: {state['status']}")
                return
            queue.put(state['moves'])


def _tick(*args, delay=0):
    while True:
        for t in args:
            t.tick()
        sleep(delay)


def _main(args: argparse.Namespace):
    _init_logging(args)
    headers = {'Authorization': f'Bearer {args.token}'}
    queue = Queue()
    game_id = ''

    def _callback(board: Board):
        if board.ply:
            move = board.move_stack[-1]
            logging.info(f'Move: {move}')
            requests.post(
                f'https://lichess.org/api/board/game/{game_id}/move/{move}',
                headers=headers)

    recognizer = BoardApiMoveRecognizer(_callback, args.move_delay)
    usb_board = USBBoard(recognizer.on_event, args.port, args.baud_rate)

    logging.debug('Connecting to board')
    with ThreadPoolExecutor() as executor, usb_board.connect():
        logging.debug('Starting _watch_events')
        executor.submit(_watch_events, queue, headers)
        logging.debug('Starting ticks')
        executor.submit(_tick, usb_board, recognizer, delay=args.move_delay / 5000)
        while True:
            item = queue.get()
            if isinstance(item, dict):
                if item['type'] == 'gameStart':
                    if item['game']['compat']['board']:
                        game_id = item['game']['id']
                        logging.info(f'Game {game_id} started')
                        executor.submit(_watch_moves, queue, headers, game_id)
                    else:
                        logging.warning(
                            f"Board incompatible game {item['game']['id']}")
                elif item['type'] == 'gameFinish':
                    logging.debug(f"gameFinish {item['game']['id']}")
                    if item['game']['id'] == game_id:
                        logging.debug(f'Game {game_id} finished')
                        game_id = ''
            elif isinstance(item, str):
                recognizer.handle_streamed_moves(item)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, parents=[ARGUMENT_PARSER])
    parser.add_argument('-t', '--token', type=str, help='Personal Access Token')
    parser.add_argument('-D', '--debug', type=str, default='info', help='Debug mode')
    try:
        _main(parser.parse_args())
    except KeyboardInterrupt:
        pass
