#!/usr/bin/env bash

set -eux

# install package & dev tools
uv sync --locked

# check code style
uv run ruff check .
uv run ruff format --check .

# run tests
uv run ./scripts/tester.sh

set +eux
