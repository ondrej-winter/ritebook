import hashlib
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

REVISION = "a" * 40
INDEX_CONTENT = b'{"schema_version":1,"skills":[]}'
INDEX_DIGEST = f"sha256:{hashlib.sha256(INDEX_CONTENT).hexdigest()}"


class GitObjectRunner:
    def __init__(self, *, committed_index: bytes = INDEX_CONTENT) -> None:
        self.committed_index = committed_index
        self.missing_revision = False
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
        self.commands.append(list(command))
        if "cat-file" in command:
            returncode = 1 if self.missing_revision else 0
            return subprocess.CompletedProcess(command, returncode, b"", b"")
        return subprocess.CompletedProcess(command, 0, self.committed_index, b"")


class SnapshotExporter:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str, Path]] = []

    def __call__(self, repository: Path, revision: str, destination: Path) -> None:
        self.calls.append((repository, revision, destination))
        skill = destination / "skills" / "code-review"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("bound content", encoding="utf-8")


def registered_skill_index(
    tmp_path: Path,
    *,
    source_type: str = "git_url",
    source: str = "git@example.com:company/skills.git",
    source_revision: str = REVISION,
    index_digest: str = INDEX_DIGEST,
) -> RegisteredSkillIndex:
    repository = tmp_path / "repository"
    repository.mkdir(exist_ok=True)
    cached_index = tmp_path / "ritebook-index.json"
    cached_index.write_bytes(INDEX_CONTENT)
    return RegisteredSkillIndex(
        name="company-skills",
        source=source,
        source_type=source_type,
        source_revision=source_revision,
        index_digest=index_digest,
        source_cache_path=str(repository) if source_type == "git_url" else None,
        cached_index_path=str(cached_index),
        index_schema_version=1,
    )


def test_source_repository_materializes_bound_commit_and_cleans_snapshot(
    tmp_path: Path,
) -> None:
    runner = GitObjectRunner()
    exporter = SnapshotExporter()
    index = registered_skill_index(tmp_path)

    adapter = SourceRepositoryAdapter(runner, exporter=exporter)
    with adapter.open_source(index) as source:
        snapshot = Path(source.repository_path)
        assert source.source_revision == REVISION
        assert (snapshot / "skills" / "code-review" / "SKILL.md").read_text() == (
            "bound content"
        )
        assert snapshot.exists()

    assert not snapshot.exists()
    repository = Path(index.source_cache_path or "")
    assert runner.commands == [
        ["git", "-C", str(repository), "cat-file", "-e", f"{REVISION}^{{commit}}"],
        ["git", "-C", str(repository), "show", f"{REVISION}:ritebook-index.json"],
    ]
    assert exporter.calls[0][:2] == (repository, REVISION)


def test_source_repository_rejects_cached_index_digest_mismatch_before_git(
    tmp_path: Path,
) -> None:
    runner = GitObjectRunner()
    index = registered_skill_index(tmp_path)
    Path(index.cached_index_path).write_bytes(b"tampered cache")

    with (
        pytest.raises(SkillSourceResolutionError, match="cached index digest mismatch"),
        SourceRepositoryAdapter(runner).open_source(index),
    ):
        pytest.fail("unreachable")

    assert runner.commands == []


def test_source_repository_rejects_bound_commit_index_digest_mismatch(
    tmp_path: Path,
) -> None:
    runner = GitObjectRunner(committed_index=b"different committed index")
    exporter = SnapshotExporter()

    with (
        pytest.raises(SkillSourceResolutionError, match="bound commit index mismatch"),
        SourceRepositoryAdapter(runner, exporter=exporter).open_source(
            registered_skill_index(tmp_path),
        ),
    ):
        pytest.fail("unreachable")

    assert exporter.calls == []


def test_source_repository_rejects_unavailable_bound_commit_with_guidance(
    tmp_path: Path,
) -> None:
    runner = GitObjectRunner()
    runner.missing_revision = True

    with (
        pytest.raises(SkillSourceResolutionError, match="run update-index"),
        SourceRepositoryAdapter(runner).open_source(
            registered_skill_index(tmp_path),
        ),
    ):
        pytest.fail("unreachable")


def test_source_repository_reads_local_commit_without_mutating_repository(
    tmp_path: Path,
) -> None:
    local_repo = tmp_path / "local"
    local_repo.mkdir()
    index = registered_skill_index(
        tmp_path,
        source_type="local_git_repo",
        source=str(local_repo),
    )
    runner = GitObjectRunner()
    exporter = SnapshotExporter()

    adapter = SourceRepositoryAdapter(runner, exporter=exporter)
    with adapter.open_source(index) as source:
        assert source.source_revision == REVISION

    assert all(
        "checkout" not in command and "fetch" not in command
        for command in runner.commands
    )
    assert exporter.calls[0][0] == local_repo


def test_source_repository_rejects_missing_local_repository_with_guidance(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    index = registered_skill_index(
        tmp_path,
        source_type="local_git_repo",
        source=str(missing),
    )

    with (
        pytest.raises(SkillSourceResolutionError, match=r"restore.*update-index"),
        SourceRepositoryAdapter(GitObjectRunner()).open_source(index),
    ):
        pytest.fail("unreachable")
