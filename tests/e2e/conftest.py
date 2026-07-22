from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Protocol

import pytest


@dataclass(frozen=True)
class CliResult:
    """Captured result from invoking the real Ritebook CLI."""

    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    def assert_success(self) -> None:
        """Assert that the CLI command succeeded with diagnostic output."""
        assert self.returncode == 0, self.format_failure()

    def assert_failure(self) -> None:
        """Assert that the CLI command failed with diagnostic output."""
        assert self.returncode != 0, self.format_failure()

    def format_failure(self) -> str:
        """Format command output for readable pytest assertion failures."""
        return (
            f"command: {' '.join(self.command)}\n"
            f"returncode: {self.returncode}\n"
            f"stdout:\n{self.stdout}\n"
            f"stderr:\n{self.stderr}"
        )


@dataclass(frozen=True)
class GitRepository:
    """Temporary local Git repository used by black-box E2E tests."""

    path: Path

    def commit_all(self, message: str) -> None:
        """Commit all repository changes with a deterministic commit message."""
        run_git(self.path, "add", ".")
        run_git(self.path, "commit", "--message", message)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CliRunner(Protocol):
    """Callable contract for invoking the real Ritebook CLI."""

    def __call__(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
    ) -> CliResult:
        """Run Ritebook with arguments and an optional working directory."""


SkillWriter = Callable[[str, str], Path]
InvalidSkillWriter = Callable[[str], Path]
GitRepositoryFactory = Callable[[Path], GitRepository]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark all tests collected from this package as E2E tests."""
    for item in items:
        if "tests/e2e" in item.path.as_posix():
            item.add_marker(pytest.mark.e2e)


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    """Return an explicit temporary Ritebook registry path."""
    return tmp_path / "config" / "indexes.json"


@pytest.fixture
def cache_root(tmp_path: Path) -> Path:
    """Return an explicit temporary Ritebook cache root."""
    return tmp_path / "cache"


@pytest.fixture
def run_cli(tmp_path: Path) -> CliRunner:
    """Return a helper that invokes the real Ritebook CLI through uv."""
    home = tmp_path / "home"
    config_home = tmp_path / "config-home"
    cache_home = tmp_path / "cache-home"
    home.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "user.name",
            "GIT_CONFIG_KEY_1": "user.email",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_VALUE_0": "Ritebook E2E",
            "GIT_CONFIG_VALUE_1": "ritebook-e2e@example.invalid",
            "HOME": str(home),
            "XDG_CACHE_HOME": str(cache_home),
            "XDG_CONFIG_HOME": str(config_home),
        },
    )

    def run(arguments: Sequence[str], *, cwd: Path | None = None) -> CliResult:
        command = (
            "uv",
            "run",
            "--frozen",
            "--no-sync",
            "--project",
            str(PROJECT_ROOT),
            "ritebook",
            *arguments,
        )
        completed = subprocess.run(  # noqa: S603 - E2E tests intentionally drive the local CLI.
            command,
            check=False,
            capture_output=True,
            cwd=cwd,
            env=environment,
            text=True,
        )
        return CliResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    return run


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    """Return the temporary skills root shared by skill writer fixtures."""
    return tmp_path / "skills"


@pytest.fixture
def write_valid_skill(skills_root: Path) -> SkillWriter:
    """Return a helper that writes a minimal valid Agent Skill file."""

    def write(name: str, description: str) -> Path:
        skill_file = skills_root / name / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(valid_skill_content(name, description), encoding="utf-8")
        return skill_file

    return write


@pytest.fixture
def write_invalid_skill(skills_root: Path) -> InvalidSkillWriter:
    """Return a helper that writes a skill with one stable metadata failure."""

    def write(name: str) -> Path:
        skill_file = skills_root / name / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(invalid_skill_content(name), encoding="utf-8")
        return skill_file

    return write


@pytest.fixture
def git_repository() -> GitRepositoryFactory:
    """Return a helper that initializes a deterministic local Git repository."""

    def create(path: Path) -> GitRepository:
        path.mkdir(parents=True, exist_ok=True)
        run_git(path, "init")
        run_git(path, "config", "user.name", "Ritebook E2E")
        run_git(path, "config", "user.email", "ritebook-e2e@example.invalid")
        return GitRepository(path=path)

    return create


def valid_skill_content(name: str, description: str) -> str:
    """Build minimal valid Agent Skill markdown content."""
    return f"""---
name: {name}
description: {description}
metadata:
  version: "1.0.0"
  dependencies:
    tools:
      - name: git
        purpose: Inspect version-control state.
        required: true
    skills: []
---
# {name}
"""


def invalid_skill_content(name: str) -> str:
    """Build Agent Skill markdown with a stable missing-description failure."""
    return f"""---
name: {name}
metadata:
  version: "1.0.0"
  dependencies:
    tools: []
    skills: []
---
# {name}
"""


def run_git(
    repository: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run a Git command inside a temporary repository."""
    git = which("git")
    if git is None:
        message = "git executable is required for E2E tests"
        raise RuntimeError(message)

    return subprocess.run(  # noqa: S603 - E2E tests intentionally drive local Git.
        (git, "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
