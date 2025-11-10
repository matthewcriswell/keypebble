.PHONY: fmt lint test check clean

fmt:
	black src tests
	ruff check --fix src tests

lint:
	ruff check src tests

test:
	pytest -q

check:
	pre-commit run --all-files

all: fmt test check

clean:
	rm -rf src/keypebble/__pycache__
	rm -rf src/keypebble/core/__pycache__
	rm -rf tests/__pycache__
	rm -rf src/keypebble.egg-info
	rm -rf dist/
