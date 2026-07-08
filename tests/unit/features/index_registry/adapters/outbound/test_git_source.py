import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from ritebook.features.index_registry.adapters.outbound.git import GitSourceAdapter
from ritebook.features.index_registry.application.dtos import IndexSourceType
from ritebook.features.index_registry.application.errors import IndexSourceError


class RecordingRunner:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, self.returncode, "", "")


def test_git_source_adapter_accepts_local_git_repo(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    runner = RecordingRunner()

    result = GitSourceAdapter(runner).prepare_source(
        str(tmp_path),
        str(tmp_path / "cache"),
    )

    assert result.source_type is IndexSourceType.LOCAL_GIT_REPO
    assert result.repository_path == str(tmp_path)
    assert result.source_cache_path is None
    assert runner.commands == []


def test_git_source_adapter_rejects_local_non_git_repo(tmp_path: Path) -> None:
    with pytest.raises(IndexSourceError, match="must be a Git repository"):
        GitSourceAdapter(RecordingRunner()).prepare_source(str(tmp_path), None)


def test_git_source_adapter_clones_git_url_to_hashed_cache(tmp_path: Path) -> None:
    runner = RecordingRunner()

    result = GitSourceAdapter(runner).prepare_source(
        "git@example.com:company/skills.git",
        str(tmp_path),
    )

    assert result.source_type is IndexSourceType.GIT_URL
    assert result.source_cache_path is not None
    assert "git@example.com" not in result.source_cache_path
    assert runner.commands == [
        [
            "git",
            "clone",
            "--",
            "git@example.com:company/skills.git",
            result.source_cache_path,
        ],
    ]


def test_git_source_adapter_refreshes_existing_clone(tmp_path: Path) -> None:
    clone_path = tmp_path / "git" / "source-id"
    clone_path.mkdir(parents=True)
    runner = RecordingRunner()

    GitSourceAdapter(runner).refresh_source(
        source="git@example.com:company/skills.git",
        source_cache_path=str(clone_path),
        cache_root=str(tmp_path),
    )

    assert runner.commands == [
        ["git", "-C", str(clone_path), "fetch", "--prune", "--tags"],
        ["git", "-C", str(clone_path), "pull", "--ff-only"],
    ]


def test_git_source_adapter_translates_git_failures(tmp_path: Path) -> None:
    with pytest.raises(IndexSourceError, match="git source operation failed"):
        GitSourceAdapter(RecordingRunner(returncode=1)).prepare_source(
            "git@example.com:company/skills.git",
            str(tmp_path),
        )
