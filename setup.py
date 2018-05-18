#!/usr/bin/env python

from setuptools import setup

setup(
    name='norsu',
    version='0.1',
    packages=['norsu'],
    license='PostgreSQL',
    entry_points={
        'console_scripts': ['norsu = norsu.main:main']
    }
)
