.DEFAULT_GOAL := help

.PHONY: help setup install-hooks format format-check lint lint-fix type architecture test quality build \
	docker-e2e-build docker-e2e-run docker-e2e verify pre-commit commit deps-tree deps-outdated deps-audit

FABRICA_GLOBAL_OPTIONS ?= --verbose-diagnostics
DOCKER_E2E_IMAGE ?= ritebook-e2e

help: ## Show available targets
	@echo "Available targets:"
	@echo "  make setup             Install locked development dependencies"
	@echo "  make install-hooks     Install the Git pre-commit hook"
	@echo "  make format            Format Python code with Ruff"
	@echo "  make format-check      Check Python formatting with Ruff"
	@echo "  make lint              Run Ruff lint checks"
	@echo "  make lint-fix          Apply Ruff lint fixes"
	@echo "  make type              Run ty type checking"
	@echo "  make architecture      Check import architecture contracts"
	@echo "  make test              Run default tests (Docker E2E excluded)"
	@echo "  make quality           Run the standard local quality gate"
	@echo "  make build             Check the lockfile and build distributions"
	@echo "  make docker-e2e-build  Build the clean Docker E2E image"
	@echo "  make docker-e2e-run    Run the clean Docker E2E image"
	@echo "  make docker-e2e        Build and run Docker E2E"
	@echo "  make verify            Run quality, build, and Docker E2E"
	@echo "  make pre-commit        Run all configured pre-commit hooks"
	@echo "  make commit            Run pre-commit and create a confirmed Fabrica commit"
	@echo "  make deps-tree         Show the full dependency tree"
	@echo "  make deps-outdated     Show outdated top-level dependencies"
	@echo "  make deps-audit        Audit locked dependencies with uv (preview)"

setup: ## Install locked development dependencies
	uv sync --locked --group dev

install-hooks: ## Install the Git pre-commit hook
	uv run --locked pre-commit install

format: ## Format Python code with Ruff
	uv run --locked ruff format .

format-check: ## Check Python formatting with Ruff
	uv run --locked ruff format --check .

lint: ## Run Ruff lint checks
	uv run --locked ruff check .

lint-fix: ## Apply Ruff lint fixes
	uv run --locked ruff check . --fix

type: ## Run ty type checking
	uv run --locked ty check src/ritebook

architecture: ## Check import architecture contracts
	uv run --locked lint-imports

test: ## Run the default test suite; Docker E2E requires explicit opt-in
	uv run --locked pytest

quality: ## Run the standard local quality gate
	@$(MAKE) --no-print-directory format-check
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory type
	@$(MAKE) --no-print-directory architecture
	@$(MAKE) --no-print-directory test

build: ## Check the lockfile and build distributions
	uv lock --check
	uv build

docker-e2e-build: ## Build the clean Docker E2E image
	docker build -f Dockerfile.e2e -t $(DOCKER_E2E_IMAGE) .

docker-e2e-run: ## Run the clean Docker E2E image
	docker run --rm $(DOCKER_E2E_IMAGE)

docker-e2e: ## Build and run Docker E2E
	@$(MAKE) --no-print-directory docker-e2e-build
	@$(MAKE) --no-print-directory docker-e2e-run

verify: ## Run quality, build, and Docker E2E
	@$(MAKE) --no-print-directory quality
	@$(MAKE) --no-print-directory build
	@$(MAKE) --no-print-directory docker-e2e

pre-commit: ## Run all configured pre-commit hooks
	uv run --locked pre-commit run --all-files

commit: ## Run pre-commit and create a confirmed commit with Fabrica
	uv run --locked fabrica $(FABRICA_GLOBAL_OPTIONS) commit \
	  --skill conventional-commits \
	  --skill-root .agents/skills \
	  --model gpt-6-luna \
	  --reasoning-effort low

deps-tree: ## Show the full dependency tree
	uv tree --locked

deps-outdated: ## Show outdated top-level dependencies
	uv tree --locked --depth 1 --outdated

deps-audit: ## Audit dependencies for known vulnerabilities
	uv audit --locked --preview-features audit-command
