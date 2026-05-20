PYTHON := .venv/bin/python
PIP    := .venv/bin/pip

.PHONY: venv install install-dev download-data train serve test lint

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install -r requirements.txt

install-dev: venv
	$(PIP) install -r requirements.txt -r requirements-dev.txt

download-data:
	bash data/download.sh

train:
	$(PYTHON) -m train.train

serve:
	$(PYTHON) -m uvicorn serve.app:app --host 0.0.0.0 --port 8001 --reload

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check .
