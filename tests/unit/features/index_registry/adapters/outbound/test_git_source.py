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
        elif "symbolic-ref" in command:
            stdout = b"refs/remotes/origin/main\n" if "refs/remotes/origin/HEAD" in command else b"refs/heads/main\n"
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
    assert result.source_branch == "refs/heads/main"
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
        [
            "git",
            "-C",
            str(tmp_path),
            "symbolic-ref",
            "--quiet",
            "HEAD",
        ],
        [
            "git",
            "-C",
            str(tmp_path),
            "rev-parse",
            "--verify",
            "refs/heads/main^{commit}",
        ],
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
    assert result.source_branch == "refs/heads/main"
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
            "symbolic-ref",
            "--quiet",
            "refs/remotes/origin/HEAD",
        ],
        [
            "git",
            "-C",
            result.source_cache_path,
            "rev-parse",
            "--verify",
            "refs/remotes/origin/main^{commit}",
        ],
        [
            "git",
            "-C",
            result.source_cache_path,
            "show",
            f"{'a' * 40}:ritebook-index.json",
        ],
    ]


@pytest.mark.parametrize(
    "source",
    [
        "https://user:sentinel-secret@example.com/company/skills.git",
        "https://sentinel-token@example.com/company/skills.git",
        "https://user%40example.com:sentinel-secret@example.com/company/skills.git",
        "ssh://git@example.com/company/skills.git",
    ],
)
def test_git_source_adapter_rejects_url_user_info_before_git_or_cache_mutation(
    tmp_path: Path,
    source: str,
) -> None:
    runner = RecordingRunner()

    with pytest.raises(IndexSourceError) as exc_info:
        GitSourceAdapter(runner).prepare_source(source, str(tmp_path))

    assert "credentials" in str(exc_info.value)
    assert "sentinel" not in str(exc_info.value)
    assert runner.commands == []
    assert list(tmp_path.iterdir()) == []


def test_git_source_adapter_accepts_scp_like_ssh_username(tmp_path: Path) -> None:
    runner = RecordingRunner()

    result = GitSourceAdapter(runner).prepare_source(
        "git@example.com:company/skills.git",
        str(tmp_path),
    )

    assert result.source == "git@example.com:company/skills.git"
    assert runner.commands[0][3] == "git@example.com:company/skills.git"


def test_git_source_adapter_refreshes_existing_clone(tmp_path: Path) -> None:
    clone_path = tmp_path / "git" / "source-id"
    clone_path.mkdir(parents=True)
    runner = RecordingRunner()

    GitSourceAdapter(runner).refresh_source(
        source="git@example.com:company/skills.git",
        source_cache_path=str(clone_path),
        cache_root=str(tmp_path),
        source_branch="refs/heads/main",
    )

    assert runner.commands == [
        [
            "git",
            "-C",
            str(clone_path),
            "fetch",
            "--prune",
            "--tags",
            "origin",
            "+refs/heads/main:refs/remotes/origin/main",
        ],
        [
            "git",
            "-C",
            str(clone_path),
            "rev-parse",
            "--verify",
            "refs/remotes/origin/main^{commit}",
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
        source_branch="refs/heads/main",
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
            source_branch="refs/heads/main",
        )


def test_git_source_adapter_translates_git_failures(tmp_path: Path) -> None:
    with pytest.raises(IndexSourceError, match="git source operation failed"):
        GitSourceAdapter(RecordingRunner(returncode=1)).prepare_source(
            "git@example.com:company/skills.git",
            str(tmp_path),
        )


def test_git_source_adapter_does_not_expose_credential_bearing_git_failure(
    tmp_path: Path,
) -> None:
    sentinel = "sentinel-secret"

    def failing_runner(command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            command,
            1,
            f"remote output {sentinel}".encode(),
            f"fatal: authentication failed for {sentinel}".encode(),
        )

    with pytest.raises(IndexSourceError) as exc_info:
        GitSourceAdapter(failing_runner).prepare_source(
            "https://example.com/company/skills.git",
            str(tmp_path),
        )

    assert str(exc_info.value) == "git source operation failed"
    assert sentinel not in str(exc_info.value)


def test_git_source_force_refresh_uses_fresh_managed_clone(tmp_path: Path) -> None:
    clone_path = tmp_path / "registries" / ("a" * 64) / "git" / ("b" * 16)
    clone_path.mkdir(parents=True)
    runner = RecordingRunner()

    result = GitSourceAdapter(runner).refresh_source(
        source="git@example.com:company/skills.git",
        source_cache_path=str(clone_path),
        cache_root=str(tmp_path),
        registry_path=str(tmp_path / "indexes.json"),
        source_branch="refs/heads/main",
        force=True,
    )

    assert clone_path.exists()
    assert result.source_cache_path != str(clone_path)
    assert runner.commands[0][:2] == ["git", "clone"]
    assert runner.commands[0][-1] == result.source_cache_path


def test_git_source_discards_only_registry_owned_managed_clone(tmp_path: Path) -> None:
    registry_path = tmp_path / "indexes.json"
    cache_root = tmp_path / "cache"
    runner = RecordingRunner()
    adapter = GitSourceAdapter(runner)
    candidate = adapter.refresh_source(
        source="git@example.com:company/skills.git",
        source_cache_path=None,
        cache_root=str(cache_root),
        registry_path=str(registry_path),
        source_branch="refs/heads/main",
        force=True,
    )
    candidate_path = Path(candidate.source_cache_path or "")
    candidate_path.mkdir(parents=True)
    (candidate_path / "managed").write_text("owned", encoding="utf-8")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    sibling = candidate_path.with_name("0" * 16)
    sibling.mkdir()

    adapter.discard_source(
        source="git@example.com:company/skills.git",
        source_cache_path=str(candidate_path),
        cache_root=str(cache_root),
        registry_path=str(registry_path),
    )
    adapter.discard_source(
        source="git@example.com:company/skills.git",
        source_cache_path=str(unrelated),
        cache_root=str(cache_root),
        registry_path=str(registry_path),
    )
    adapter.discard_source(
        source="git@example.com:company/skills.git",
        source_cache_path=str(sibling),
        cache_root=str(cache_root),
        registry_path=str(registry_path),
    )

    assert not candidate_path.exists()
    assert sibling.exists()
    assert unrelated.exists()
