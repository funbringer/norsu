#!/usr/bin/env python

from setuptools import setup

install_requires=['toml']

setup(
    name='norsu',
    version='0.1',
    packages=['norsu'],
    license='PostgreSQL',
    install_requires=install_requires,
    entry_points={
        'console_scripts': ['norsu = norsu.main:main']
    }
)
