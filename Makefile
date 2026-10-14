.PHONY: all
all: lint fmt typecheck

.PHONY: sync
sync:
	uv sync --locked

.PHONY: fmt
fmt: sync
	uv run ruff format .

.PHONY: lint
lint: sync
	uv run ruff check .

.PHONY: typecheck
typecheck: sync
	uv run mypy norsu

.PHONY: test
test: sync
	uv run ./scripts/tester.sh

.PHONY: build
build:
	uv build

.PHONY: install
install:
	uv tool install --reinstall .
