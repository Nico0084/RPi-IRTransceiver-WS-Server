#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" 
============== This file is part of DAIKIN PAC Controler project $

License
=======

B(Rpi_IR_Transceiver} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Rpi_IR_Transceiver} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Program purpose
==============

Can receive/send IR code RAW (pulse/pause pairs) and communicate with client by using WebSocket server in JSON format.

Implements
==========
"""

from setuptools import setup, find_packages

setup(
    name = 'Rpi_IRTransceiver',
    version = '0.1.0',
    url = 'https://github.com/Nico0084/RPi-IRTransceiver-WS-Server',
    description = 'OpenSource Raspberry IR Controler software',
    author = 'Nico84dev',
    author_email = 'nico84dev at gmail.com',
    install_requires=['setuptools',
          'RPi.GPIO >= 0.5.5',
          'ws4py >= 0.3.2',
          'wsgiref >= 0.1.2',
	      ],
    zip_safe = False,
    license = 'GPL v3',
    #include_package_data = True,
    packages = find_packages(),
    package_data = {},
    scripts=[],
    entry_points = {
        'console_scripts': [
	    """
            irtransceiver = bin.ir_transceiver:main
	    """
        ]
        },
    data_files=[('/etc/init.d/', ['init/irtransceiver'])], 
    classifiers=[
        "Topic :: Home Automation",
        "Environment :: Input/Output GPIO (Daemon)",
        "Programming Language :: Python",
        "Development Status :: 1 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: French"
    ]
)
