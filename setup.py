#!/usr/bin/env python3
import os
from setuptools import setup

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name='mqtt_otgw',
    version='20180707.1',
    url='https://github.com/fliphess/py-otgw-influxdb.git',
    author_email='undef',
    description='py-otgw-influxdb',
    install_requires=[
        'PyYAML',
        'paho-mqtt',
        'pid',
        'requests',
        'influxdb',
        'websocket'
    ],
    packages=[
        'otgw_influxdb',
    ],
    entry_points=dict(console_scripts=[
        'otgw-influx-collector = otgw_influxdb.main:main',
    ]),
)
