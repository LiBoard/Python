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

"""LiBoard submodule for communication with physical boards."""
from abc import ABC, abstractmethod
from asyncio import Queue, StreamReader, StreamReaderProtocol, get_event_loop

from serial_asyncio import create_serial_connection

from liboard import Bitboard


class PhysicalBoard(ABC):
    """Abstract class for physical electronic chessboards."""

    def __init__(self, bitboard_q: Queue, configurable: bool = False):
        """
        Create a new PhysicalBoard.

        :param bitboard_q: Queue to put incoming Bitboards in
        :param configurable: whether the board can be communicated with
            in order to change its settings
        """
        self._bitboard_q: Queue = bitboard_q
        self._configurable: bool = configurable

    @property
    def is_configurable(self):
        """Whether the board can be communicated with in order to change its settings."""
        return self._configurable

    @abstractmethod
    async def watch_incoming(self):
        """Watch for incoming Bitboards."""
        pass


class USBBoard(PhysicalBoard):
    """Represents a board which is connected via USB and communicated with via pyserial."""

    def __init__(self, bitboard_q: Queue, port: str = '/dev/ttyACM0',
                 baud_rate: int = 9600, configurable: bool = False):
        """
        Create a new USBBoard.

        :param bitboard_q: Queue to put incoming Bitboards in
        :param configurable: whether the board can be communicated with
            in order to change its settings
        :param port: the port which the baord is connected to
        :param baud_rate: the baud_rate to use for communication with the board
        """
        super().__init__(bitboard_q, configurable)
        self._port: str = port
        self._baud_rate: int = baud_rate

    async def watch_incoming(self):
        """Watch for incoming Bitboards."""
        loop = get_event_loop()
        reader = StreamReader(loop=loop)
        await create_serial_connection(loop, lambda: StreamReaderProtocol(reader, loop=loop),
                                       self._port, baudrate=self._baud_rate)
        while True:
            await self._bitboard_q.put(Bitboard(await reader.readexactly(8)))
