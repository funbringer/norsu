#!/usr/bin/env bash

set -eux

PYTHON_VENV=/tmp/venv

virtualenv --python=python3 $PYTHON_VENV
export VIRTUAL_ENV_DISABLE_PROMPT=1
source $PYTHON_VENV/bin/activate

pip install flake8

# check code style
flake8 .

# install package
pip install -U .

# run tests
./tester.sh

deactivate
rm -rf $PYTHON_VENV

set +eux
