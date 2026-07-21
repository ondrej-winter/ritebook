import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from ritebook.features.index_registry.adapters.outbound.git import GitSourceAdapter
from ritebook.features.index_registry.application.dtos import IndexSourceType
from ritebook.features.index_registry.application.errors import IndexSourceError


class RecordingRunner:
    def __init__(
        self,
        returncode: int = 0,
        *,
        dirty: bool = False,
        revision: bytes = b"a" * 40,
        index_content: bytes = b'{"schema_version":1}',
        failing_operation: str | None = None,
    ) -> None:
        self.returncode = returncode
        self.dirty = dirty
        self.revision = revision
        self.index_content = index_content
        self.failing_operation = failing_operation
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
        self.commands.append(list(command))
        returncode = self.returncode
        if self.failing_operation and self.failing_operation in command:
            returncode = 1
        stdout = b""
        if "status" in command and self.dirty:
            stdout = b"?? untracked.txt\n"
        elif "rev-parse" in command:
            stdout = self.revision + b"\n"
        elif "show" in command:
            stdout = self.index_content
        return subprocess.CompletedProcess(command, returncode, stdout, b"")


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
    assert result.source_revision == "a" * 40
    assert result.index_content == b'{"schema_version":1}'
    assert runner.commands == [
        [
            "git",
            "-C",
            str(tmp_path),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        ["git", "-C", str(tmp_path), "rev-parse", "--verify", "HEAD^{commit}"],
        [
            "git",
            "-C",
            str(tmp_path),
            "show",
            f"{'a' * 40}:ritebook-index.json",
        ],
    ]


def test_git_source_adapter_rejects_dirty_local_git_repo(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    with pytest.raises(IndexSourceError, match="commit or discard"):
        GitSourceAdapter(RecordingRunner(dirty=True)).prepare_source(
            str(tmp_path),
            None,
        )


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
        [
            "git",
            "-C",
            result.source_cache_path,
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        ],
        [
            "git",
            "-C",
            result.source_cache_path,
            "show",
            f"{'a' * 40}:ritebook-index.json",
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
        [
            "git",
            "-C",
            str(clone_path),
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        ],
        [
            "git",
            "-C",
            str(clone_path),
            "show",
            f"{'a' * 40}:ritebook-index.json",
        ],
    ]


def test_git_source_adapter_reads_index_from_selected_revision(tmp_path: Path) -> None:
    clone_path = tmp_path / "git" / "source-id"
    clone_path.mkdir(parents=True)
    runner = RecordingRunner(revision=b"b" * 40, index_content=b"committed bytes")

    result = GitSourceAdapter(runner).refresh_source(
        source="git@example.com:company/skills.git",
        source_cache_path=str(clone_path),
        cache_root=str(tmp_path),
    )

    assert result.source_revision == "b" * 40
    assert result.index_content == b"committed bytes"
    assert runner.commands[-1][-1] == f"{'b' * 40}:ritebook-index.json"


def test_git_source_adapter_rejects_unavailable_source_revision(tmp_path: Path) -> None:
    clone_path = tmp_path / "git" / "source-id"
    clone_path.mkdir(parents=True)

    with pytest.raises(IndexSourceError, match="git source operation failed"):
        GitSourceAdapter(RecordingRunner(failing_operation="rev-parse")).refresh_source(
            source="git@example.com:company/skills.git",
            source_cache_path=str(clone_path),
            cache_root=str(tmp_path),
        )


def test_git_source_adapter_translates_git_failures(tmp_path: Path) -> None:
    with pytest.raises(IndexSourceError, match="git source operation failed"):
        GitSourceAdapter(RecordingRunner(returncode=1)).prepare_source(
            "git@example.com:company/skills.git",
            str(tmp_path),
        )
