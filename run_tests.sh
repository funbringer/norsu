#!/usr/bin/env bash

virtualenv --python=python3 /tmp/venv
source /tmp/venv/bin/activate

# install package
pip install -U .

# run tests
./tester.sh

if [ -f regression.diffs ]; then
	echo
	echo "========"
	echo " Diffs:"
	echo "========"
	echo
	cat regression.diffs
fi
