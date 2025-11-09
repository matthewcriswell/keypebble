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
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
