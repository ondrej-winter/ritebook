from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import which

import pytest


@dataclass(frozen=True)
class GitRepository:
    """Temporary local Git repository for adapter integration tests."""

    path: Path

    def commit_all(self, message: str) -> str:
        """Commit all repository changes and return the resulting revision."""
        run_git(self.path, "add", ".")
        run_git(self.path, "commit", "--message", message)
        return git_head(self.path)


GitRepositoryFactory = Callable[[Path], GitRepository]
SkillWriter = Callable[[str, str], Path]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark all tests collected from this package as integration tests."""
    for item in items:
        if "tests/integration" in item.path.as_posix():
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    """Return a temporary root containing skill directories."""
    return tmp_path / "skills"


@pytest.fixture
def write_valid_skill(skills_root: Path) -> SkillWriter:
    """Return a helper that writes a minimal valid skill file."""

    def write(name: str, description: str) -> Path:
        skill_file = skills_root / name / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(valid_skill_content(name, description), encoding="utf-8")
        return skill_file

    return write


@pytest.fixture
def git_repository() -> GitRepositoryFactory:
    """Return a helper that initializes a local Git repository."""

    def create(path: Path) -> GitRepository:
        path.mkdir(parents=True, exist_ok=True)
        run_git(path, "init")
        run_git(path, "config", "user.name", "Ritebook Integration")
        run_git(path, "config", "user.email", "ritebook-integration@example.invalid")
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
    tools: []
    skills: []
---
# {name}
"""


def git_head(repository: Path) -> str:
    """Return the current Git HEAD revision."""
    result = run_git(repository, "rev-parse", "HEAD")
    return result.stdout.strip()


def run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run Git in a temporary repository."""
    git = which("git")
    if git is None:
        message = "git executable is required for integration tests"
        raise RuntimeError(message)

    return subprocess.run(  # noqa: S603 - integration tests intentionally drive local Git.
        (git, "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
