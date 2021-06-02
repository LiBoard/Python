#! /usr/bin/python3

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
