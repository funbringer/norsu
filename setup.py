#!/usr/bin/env python

from setuptools import setup

install_requires = ['toml', 'testgres']

setup(
    name='norsu',
    version='0.1',
    packages=['norsu'],
    package_data={'norsu': ['data/*']},
    license='MIT',
    install_requires=install_requires,
    entry_points={
        'console_scripts': ['norsu = norsu.main:main']
    }
)
