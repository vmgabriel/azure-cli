# azure-cli — development tasks. All tooling runs inside Hatch environments.
.DEFAULT_GOAL := help

HATCH ?= hatch

.PHONY: help install hooks test test-unit test-integration lint format build clean

help: ## Show azure-cli development commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install project (editable) + dev dependencies via hatch
	$(HATCH) env create
	$(HATCH) run python -m pip install -e ".[dev]"

hooks: ## Install the pre-commit git hooks
	$(HATCH) run pre-commit install

test: ## Run all tests (unit + integration) with coverage
	$(HATCH) run pytest --cov=azure_cli --cov-report=term-missing --cov-fail-under=80

test-unit: ## Run unit tests only
	$(HATCH) run pytest tests/unit --cov=azure_cli --cov-report=term-missing --cov-fail-under=0

test-integration: ## Run integration tests (live API tests need AZURE_DEVOPS_PAT)
	$(HATCH) run pytest tests/integration --cov=azure_cli --cov-report=term-missing --cov-fail-under=0 --run-live

lint: ## Run ruff check, ruff format (check mode) and mypy
	$(HATCH) run ruff check .
	$(HATCH) run ruff format --check .
	$(HATCH) run mypy

format: ## Apply ruff autofixes and formatting
	$(HATCH) run ruff check --fix .
	$(HATCH) run ruff format .

build: ## Build sdist + wheel with hatch
	$(HATCH) build

clean: ## Remove build artifacts, caches and coverage files
	rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
