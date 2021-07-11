#!/usr/bin/env python

import norsu
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

install_requires = ['toml', 'testgres']

# Get contents of README file
with open('README.md', 'r') as f:
    readme = f.read()

setup(name='norsu',
      version=norsu.__version__,
      packages=['norsu'],
      package_data={'norsu': ['data/*']},
      license='MIT',
      author='Dmitry Ivanov',
      url='https://github.com/funbringer/norsu',
      long_description=readme,
      long_description_content_type='text/markdown',
      description='PostgreSQL builds manager',
      keywords=['PostgreSQL', 'postgres', 'install', 'test'],
      install_requires=install_requires,
      entry_points={'console_scripts': ['norsu = norsu.main:main']})
