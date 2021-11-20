#! /usr/bin/python3

"""Print the binary data from the Arduino as it comes in."""

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

from liboard import Bitboard
from liboard.physical import USBBoard


def _callback(bitboard: Bitboard):
    print(bitboard.bits.bin)


def _main(args):
    board = USBBoard(_callback, args.port, args.baud_rate)

    with board.connection():
        while True:
            board.tick()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-p', '--port', default='/dev/ttyACM0',
                        help='The serial port which the board is connected to ' +
                             '(Default /dev/ttyACM0)')
    parser.add_argument('-b', '--baud-rate', default=9600, type=int,
                        help='The board\'s baud rate (Default 9600)')
    _main(parser.parse_args())
