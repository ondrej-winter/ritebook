from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

E2E_MARKER = "e2e"
DOCKER_E2E_ENVIRONMENT = "RITEBOOK_DOCKER_E2E"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the explicit opt-in required to collect Docker E2E tests."""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="run Docker-only E2E tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register E2E metadata and reject opt-in outside the Docker runner."""
    config.addinivalue_line(
        "markers",
        "e2e: black-box tests of the wheel-installed CLI and process boundaries",
    )
    validate_e2e_execution(
        run_e2e=config.getoption("--run-e2e"),
        docker_e2e=os.environ.get(DOCKER_E2E_ENVIRONMENT) == "1",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Mark E2E tests and deselect them unless execution was explicitly enabled."""
    e2e_items = [item for item in items if is_e2e_path(item.path)]
    for item in e2e_items:
        item.add_marker(E2E_MARKER)

    if config.getoption("--run-e2e") or not e2e_items:
        return

    e2e_item_ids = {id(item) for item in e2e_items}
    items[:] = [item for item in items if id(item) not in e2e_item_ids]
    config.hook.pytest_deselected(items=e2e_items)


def is_e2e_path(path: Path) -> bool:
    """Return whether a collected test path belongs to the E2E suite."""
    parts = path.parts
    return any(part == "tests" and parts[index + 1] == "e2e" for index, part in enumerate(parts[:-1]))


def validate_e2e_execution(*, run_e2e: bool, docker_e2e: bool) -> None:
    """Reject explicit E2E execution outside the clean Docker environment."""
    if run_e2e and not docker_e2e:
        raise pytest.UsageError(_docker_e2e_usage())


def _docker_e2e_usage() -> str:
    return (
        "E2E tests require the clean Docker E2E environment. Run:\n"
        "  docker build -f Dockerfile.e2e -t ritebook-e2e .\n"
        "  docker run --rm ritebook-e2e"
    )
