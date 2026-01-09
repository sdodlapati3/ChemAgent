.PHONY: help install test lint format clean docker-build docker-run

help:
	@echo "ChemAgent Development Commands"
	@echo "=============================="
	@echo "install        Install package and dependencies"
	@echo "install-dev    Install with dev dependencies"
	@echo "test           Run tests"
	@echo "test-fast      Run tests excluding slow tests"
	@echo "test-cov       Run tests with coverage report"
	@echo "lint           Run linters (ruff, mypy)"
	@echo "format         Format code (black, isort)"
	@echo "clean          Clean build artifacts"
	@echo "docker-build   Build Docker image"
	@echo "docker-run     Run Docker container"
	@echo "example        Run basic usage example"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,llm,web]"

test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v -m "not slow"

test-cov:
	pytest tests/ -v --cov=src/chemagent --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/ examples/
	isort src/ tests/ examples/

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t chemagent:latest .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

example:
	python examples/basic_usage.py
