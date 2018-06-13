#!/usr/bin/env python

import norsu
from setuptools import setup

install_requires = ['toml', 'testgres']

setup(
    name='norsu',
    version=norsu.__version__,
    packages=['norsu'],
    package_data={'norsu': ['data/*']},
    license='MIT',
    install_requires=install_requires,
    entry_points={
        'console_scripts': ['norsu = norsu.main:main']
    }
)
