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
from asyncio import Protocol, Queue, StreamReader, StreamReaderProtocol, get_event_loop
from asyncio.transports import BaseTransport
from typing import Any, Callable, Optional, Union

from bitstring import BitStream
from serial_asyncio import create_serial_connection

from liboard import Bitboard, Bits


class _BitboardProtocol(Protocol):
    def __init__(self):
        self.queue = Queue()
        self.bits = BitStream()
        self.transport: Optional[BaseTransport] = None

    def data_received(self, data: bytes):
        self.bits.append(Bits(bytes))
        if len(self.bits) >= 64:
            self.queue.put_nowait(self.bits.read('bits:64'))


class PhysicalBoard(ABC):
    """Abstract class for physical electronic chessboards."""

    def __init__(self, callback: Callable[[Union[str, Bitboard]], Any],
                 configurable: bool = False):
        """
        Create a new PhysicalBoard.

        :param callback: callback for various events
        :param configurable: whether the board can be communicated with
            in order to change its settings
        """
        self._callback: Callable[[Union[str, Bitboard]], Any] = callback
        self._configurable: bool = configurable

    @property
    def is_configurable(self):
        """Whether the board can be communicated with in order to change its settings."""
        return self._configurable

    @abstractmethod
    async def bitboards(self):
        """Yield incoming Bitboards asynchronously."""


class USBBoard(PhysicalBoard):
    """Represents a board which is connected via USB and communicated with via pyserial."""

    def __init__(self, callback: Callable[[Union[str, Bitboard]], Any], port: str = '/dev/ttyACM0',
                 baud_rate: int = 9600, configurable: bool = False):
        """
        Create a new USBBoard.

        :param port: the port which the baord is connected to
        :param baud_rate: the baud_rate to use for communication with the board
        """
        super().__init__(callback, configurable)
        self._port: str = port
        self._baud_rate: int = baud_rate

    async def bitboards(self):
        """Yield incoming Bitboards asynchronously."""
        loop = get_event_loop()
        reader = StreamReader(loop=loop)
        await create_serial_connection(loop, lambda: StreamReaderProtocol(reader, loop=loop),
                                       self._port, baudrate=self._baud_rate)
        while True:
            yield Bitboard(await reader.readexactly(8))
