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
    author='Dmitry Ivanov',
    url='https://github.com/funbringer/norsu',
    description='PostgreSQL builds manager',
    keywords=['PostgreSQL', 'postgres', 'install', 'test'],
    install_requires=install_requires,
    entry_points={
        'console_scripts': ['norsu = norsu.main:main']
    }
)
