.DEFAULT_GOAL := help

.PHONY: help format lint type test quality pre-commit commit deps-tree deps-outdated deps-audit

FABRICA_GLOBAL_OPTIONS ?= --verbose-diagnostics

help: ## Show available targets
	@echo "Available targets:"
	@echo "  make format         Format Python code with Ruff"
	@echo "  make lint           Run Ruff lint checks"
	@echo "  make type           Run ty type checking"
	@echo "  make test           Run the default non-E2E test suite"
	@echo "  make quality        Run the local quality gate"
	@echo "  make pre-commit     Run all configured pre-commit hooks"
	@echo "  make commit         Commit staged changes with Fabrica"
	@echo "  make deps-tree      Show the full dependency tree"
	@echo "  make deps-outdated  Show outdated top-level dependencies"
	@echo "  make deps-audit     Audit dependencies for known vulnerabilities"

format: ## Format Python code with Ruff
	uv run ruff format .

lint: ## Run Ruff lint checks
	uv run ruff check .

type: ## Run ty type checking
	uv run ty check src/ritebook

test: ## Run the default non-E2E test suite
	uv run pytest -m "not e2e"

quality: lint type test ## Run the local quality gate
	uv run ruff format . --check

pre-commit: ## Run all configured pre-commit hooks
	uv run pre-commit run --all-files

commit: ## Commit staged changes with Fabrica
	uv run fabrica $(FABRICA_GLOBAL_OPTIONS) commit \
	  --skill conventional-commits \
	  --skill-root .agents/skills \
	  --model gpt-5.6-luna \
	  --reasoning-effort low

deps-tree: ## Show the full dependency tree
	uv tree --frozen

deps-outdated: ## Show outdated top-level dependencies
	uv tree --frozen --depth 1 --outdated

deps-audit: ## Audit dependencies for known vulnerabilities
	mkdir -p .tmp
	uv export --frozen --no-hashes --format requirements.txt -o .tmp/requirements-audit.txt
	uvx --from pip-audit pip-audit -r .tmp/requirements-audit.txt
