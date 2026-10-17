.PHONY: test

PYTHON ?= python3

test:
	$(PYTHON) -m pytest -q
	npm --prefix frontend run build
