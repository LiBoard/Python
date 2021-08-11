#! /usr/bin/python3

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

from setuptools import setup

setup(name='liboard',
      version='0.1.1dev1',
      description='A module for interacting with LiBoard',
      url='https://github.com/PhilLecl/LiBoard',
      author='Philipp Leclercq',
      author_email='liboard@philippleclercq.eu',
      license='GPL-3.0-or-later',
      classifiers=[
          'Development Status :: 1 - Planning',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Intended Audience :: Developers',
          'Intended Audience :: Education',
          'Intended Audience :: End Users/Desktop',
          'Programming Language :: Python :: 3',
          'Topic :: Games/Entertainment :: Board Games',
          'Topic :: Games/Entertainment :: Turn Based Strategy'
      ],
      keywords=['chess', 'LiBoard', 'chessboard'],
      install_requires=['chess', 'pyserial', 'bitstring'])
