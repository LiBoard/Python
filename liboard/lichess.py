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

"""LiBoard submodule for interacting with the Lichess Board API."""
import json
import logging
from asyncio import Queue, Task, create_task
from typing import Optional

from httpx import AsyncClient


class APIConnection:
    """A connection to the API."""

    def __init__(self, token: str, recognized_move_q: Queue, streamed_move_q: Queue):
        """
        Initialize a new APIConnection.

        :param token: Personal API access token
        :param streamed_move_q: Queue to put streamed moves in
        :param recognized_move_q: Queue to get recognized moves from
        """
        self._headers = {'Authorization': f'Bearer {token}'}
        self._client: Optional[AsyncClient] = None
        self.streamed_move_queue = streamed_move_q
        self._recognized_move_queue = recognized_move_q
        self._game: Optional[Game] = None

    # region context manager
    async def __aenter__(self):
        """Open the connection."""
        if not self._client:
            self._client = AsyncClient(headers=self._headers, timeout=None)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the Connection."""
        if self._game:
            self._game.__exit__()
            self._game = None
        await self._client.aclose()
        self._client = None

    # endregion

    async def watch_recognized_moves(self):
        """Watch for recognized moves."""
        while True:
            if (board := await self._recognized_move_queue.get()).ply():
                create_task(self._send_move(str(board.move_stack[-1])))

    async def stream(self, url):
        """Yield json objects from a stream."""
        async with self._client.stream('GET', url) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    logging.debug(line)
                    yield json.loads(line)

    async def watch_events(self):
        """Watch the event stream."""
        self._ensure_open()
        async for event in self.stream('https://lichess.org/api/stream/event'):
            logging.debug(event)
            if 'game' in (event_type := event['type']):
                game = event['game']
                game_id = game['id']
                if event_type == 'gameStart':
                    if game['compat']['board']:
                        if self._game and self._game.is_open:
                            logging.info(f'Ignoring game {game_id}' +
                                         'as game {self._game.game_id} is being observed')
                        else:
                            logging.info(f'Game {game_id} started')
                            self._game = Game(game_id, self)
                    else:
                        logging.warning(f'Board incompatible game {game_id}')
                elif event_type == 'gameFinish':
                    logging.debug(f'gameFinish {game_id}')
                    if self._game and game_id == self._game.game_id:
                        self._game.__exit__()
                        self._game = None

    async def _send_move(self, move: str):
        logging.info(f'Move: {move}')
        self._ensure_open()
        await self._client.post(
            f'https://lichess.org/api/board/game/{self._game.game_id}/move/{move}')

    def _ensure_open(self):
        if not self._client:
            raise IOError('Connection must be open. Use async with to avoid this error.')


class Game:
    """Represents a game."""

    def __init__(self, game_id: str, connection: APIConnection):
        """
        Initialize a Game.

        :param game_id: the game's id
        :param connection: the connection used for API communication
        """
        self._game_id: str = game_id
        self._connection: APIConnection = connection
        self._task: Optional[Task] = None

        self.__enter__()  # start streaming the board game state immediately

    @property
    def game_id(self):
        """Return the game id."""
        return self._game_id

    @property
    def is_open(self):
        """Return whether the game is being observed."""
        return self._task and not self._task.done()

    # region context manager
    def __enter__(self):
        """Start streaming the board game state."""
        if not self._task:
            self._task = create_task(self._watch_moves())

    def __exit__(self):
        """Stop streaming the board game state."""
        if self._task:
            self._task.cancel()

    # endregion

    async def _watch_moves(self):
        async for item in self._connection.stream(
                f'https://lichess.org/api/board/game/stream/{self.game_id}'):
            logging.debug(item)
            state = item if item['type'] == 'gameState' \
                else item['state'] if item['type'] == 'gameFull' else None
            if state:
                if state['status'] != 'started':
                    logging.info(f"Status: {state['status']}")
                    return
                self._connection.streamed_move_queue.put_nowait(state['moves'])
