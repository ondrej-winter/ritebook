import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound.source_repository import (
    SourceRepositoryAdapter,
)
from ritebook.features.skill_installation.application.dtos import RegisteredSkillIndex
from ritebook.features.skill_installation.application.errors import (
    SkillSourceResolutionError,
)


class RecordingRunner:
    def __init__(self, *, returncode: int = 0, stdout: str = "abc123\n") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, "")


def registered_skill_index(
    *,
    name: str = "company-skills",
    source: str = "git@example.com:company/skills.git",
    source_type: str = "git_url",
    source_cache_path: str | None = "/cache/git/company-skills",
    cached_index_path: str = "/cache/indexes/company-skills/ritebook-index.json",
    index_schema_version: int = 1,
) -> RegisteredSkillIndex:
    return RegisteredSkillIndex(
        name=name,
        source=source,
        source_type=source_type,
        source_cache_path=source_cache_path,
        cached_index_path=cached_index_path,
        index_schema_version=index_schema_version,
    )


def test_source_repository_uses_git_url_managed_clone_path(tmp_path: Path) -> None:
    source_cache_path = tmp_path / "cache" / "git" / "source-id"
    source_cache_path.mkdir(parents=True)
    runner = RecordingRunner(stdout="def456\n")

    result = SourceRepositoryAdapter(runner).resolve_source(
        registered_skill_index(
            name="platform-skills",
            source="git@example.com:company/skills.git",
            source_type="git_url",
            source_cache_path=str(source_cache_path),
        ),
    )

    assert result.repository_path == str(source_cache_path)
    assert result.source == "git@example.com:company/skills.git"
    assert result.source_type == "git_url"
    assert result.source_revision == "def456"
    assert runner.commands == [
        ["git", "-C", str(source_cache_path), "rev-parse", "HEAD"],
    ]


def test_source_repository_uses_local_git_source_path(tmp_path: Path) -> None:
    local_repo = tmp_path / "local-skills"
    local_repo.mkdir()
    runner = RecordingRunner(stdout="local-revision\n")

    result = SourceRepositoryAdapter(runner).resolve_source(
        registered_skill_index(
            name="company-skills",
            source=str(local_repo),
            source_type="local_git_repo",
            source_cache_path=None,
        ),
    )

    assert result.repository_path == str(local_repo)
    assert result.source == str(local_repo)
    assert result.source_type == "local_git_repo"
    assert result.source_revision == "local-revision"
    assert runner.commands == [
        ["git", "-C", str(local_repo), "rev-parse", "HEAD"],
    ]


def test_source_repository_rejects_git_url_without_cache_path() -> None:
    with pytest.raises(SkillSourceResolutionError, match="no source cache path"):
        SourceRepositoryAdapter(RecordingRunner()).resolve_source(
            registered_skill_index(
                source_type="git_url",
                source_cache_path=None,
            ),
        )


def test_source_repository_rejects_missing_git_url_cache_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing"

    with pytest.raises(SkillSourceResolutionError, match="cache does not exist"):
        SourceRepositoryAdapter(RecordingRunner()).resolve_source(
            registered_skill_index(
                source_type="git_url",
                source_cache_path=str(missing_path),
            ),
        )


def test_source_repository_rejects_missing_local_source_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing"

    with pytest.raises(SkillSourceResolutionError, match="local source repository"):
        SourceRepositoryAdapter(RecordingRunner()).resolve_source(
            registered_skill_index(
                source=str(missing_path),
                source_type="local_git_repo",
                source_cache_path=None,
            ),
        )


def test_source_repository_returns_none_when_revision_cannot_be_read(
    tmp_path: Path,
) -> None:
    source_cache_path = tmp_path / "cache" / "git" / "source-id"
    source_cache_path.mkdir(parents=True)
    runner = RecordingRunner(returncode=1)

    result = SourceRepositoryAdapter(runner).resolve_source(
        registered_skill_index(
            source_type="git_url",
            source_cache_path=str(source_cache_path),
        ),
    )

    assert result.source_revision is None
    assert runner.commands == [
        ["git", "-C", str(source_cache_path), "rev-parse", "HEAD"],
    ]


def test_source_repository_rejects_unsupported_source_type(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    index = object.__new__(type(registered_skill_index()))
    object.__setattr__(index, "name", "platform-skills")
    object.__setattr__(index, "source", str(repo_path))
    object.__setattr__(index, "source_type", "archive")
    object.__setattr__(index, "source_cache_path", None)

    with pytest.raises(SkillSourceResolutionError, match="unsupported source type"):
        SourceRepositoryAdapter(RecordingRunner()).resolve_source(index)
