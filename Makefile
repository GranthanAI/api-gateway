.PHONY: help install run clean

help:
	@echo "API Gateway Makefile targets:"
	@echo "  install   - Install python dependencies using uv"
	@echo "  run       - Launch the FastAPI API Gateway local server"
	@echo "  clean     - Clean temporary python files and virtualenv"

install:
	uv sync

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

clean:
	rm -rf .venv __pycache__
