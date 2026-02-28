.PHONY: fmt lint test check clean setup

VENV   := .venv
PYTHON := python3.11
BIN    := $(VENV)/bin

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

fmt:
	$(BIN)/black src tests
	$(BIN)/ruff check --fix src tests

lint:
	$(BIN)/ruff check src tests

test:
	$(BIN)/pytest -q

check:
	$(BIN)/pre-commit run --all-files

all: fmt test check

clean:
	rm -rf src/keypebble/__pycache__
	rm -rf src/keypebble/core/__pycache__
	rm -rf src/keypebble/service/__pycache__
	rm -rf tests/__pycache__
	rm -rf src/keypebble.egg-info
	rm -rf dist/
