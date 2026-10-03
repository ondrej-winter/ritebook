from pathlib import Path

import pytest

import conftest as pytest_policy


def test_e2e_path_is_classified_for_explicit_opt_in() -> None:
    assert pytest_policy.is_e2e_path(Path("tests/e2e/test_cli_workflows.py"))
    assert not pytest_policy.is_e2e_path(Path("tests/unit/test_cli.py"))


def test_e2e_execution_requires_docker_environment() -> None:
    with pytest.raises(pytest.UsageError, match="Docker E2E environment"):
        pytest_policy.validate_e2e_execution(
            run_e2e=True,
            docker_e2e=False,
        )


def test_default_execution_does_not_require_docker_environment() -> None:
    pytest_policy.validate_e2e_execution(
        run_e2e=False,
        docker_e2e=False,
    )
