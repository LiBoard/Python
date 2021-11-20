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
from contextlib import contextmanager
from typing import Any, Callable, Optional, Union

from serial import Serial

from liboard import Bitboard


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

    @property
    @abstractmethod
    def is_connected(self):
        """Whether there's currently a connection to the board."""
        return False

    @abstractmethod
    @contextmanager
    def connection(self):
        """Connect to the board."""
        pass

    @abstractmethod
    def tick(self):
        """Check for new data and call the callback if necessary."""
        pass


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
        self._connection: Optional[Serial] = None

    @property
    def is_connected(self):
        """Whether there's currently a connection to the board."""
        return self._connection and self._connection.is_open

    @contextmanager
    def connection(self):
        """Connect to the board."""
        try:
            self._connection = Serial(self._port, self._baud_rate)
            yield self._connection
        finally:
            self._connection.close()
            self._connection = None

    def tick(self):
        """Check for new data and call the callback if necessary."""
        if self.is_connected and self._connection.in_waiting >= 8:
            self._callback(Bitboard(self._connection.read(8)))
