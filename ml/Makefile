PYTHON := .venv/bin/python
PIP    := .venv/bin/pip

.PHONY: venv install install-dev download-data train serve serve-prod test lint

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install -r requirements.txt

install-dev: venv
	$(PIP) install -r requirements.txt -r requirements-dev.txt

install-train: venv
	$(PIP) install -r requirements-train.txt

download-data:
	bash data/download.sh

train:
	$(PYTHON) -m train.train

serve:
	# 개발용 (--reload, 단일 워커)
	$(PYTHON) -m uvicorn serve.app:app --host 0.0.0.0 --port 8001 --reload

serve-prod:
	# 프로덕션용 — --reload 제거, workers=1 고정 (GPU 메모리 중복 방지)
	$(PYTHON) -m uvicorn serve.app:app --host 0.0.0.0 --port 8001 --workers 1

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check .
