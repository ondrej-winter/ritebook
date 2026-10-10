"""Subprocess-backed Git source adapter."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from ritebook.features.index_registry.adapters.outbound.cache_paths import (
    registry_cache_root,
)
from ritebook.features.index_registry.application.dtos import (
    IndexSourceType,
    PreparedIndexSource,
)
from ritebook.features.index_registry.application.errors import IndexSourceError
from ritebook.shared_kernel import require_safe_persisted_source

GitRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[bytes]]


class GitSourceAdapter:
    """Prepare and refresh Git URL and local Git repository sources."""

    def __init__(self, runner: GitRunner | None = None) -> None:
        """Initialize the adapter with an injectable Git command runner."""
        self._runner = runner or _run_git

    def prepare_source(
        self,
        source: str,
        cache_root: str | None,
        registry_path: str | None = None,
    ) -> PreparedIndexSource:
        """Prepare a source for add-index."""
        source_path = Path(source).expanduser()
        if source_path.exists():
            return self._local_source(source_path)
        _require_safe_git_url(source)
        clone_path = _managed_clone_path(source, cache_root, registry_path)
        if clone_path.exists():
            source_branch = self._canonical_branch(clone_path)
            self._refresh_clone(clone_path, source_branch)
        else:
            self._clone_source(source, clone_path)
            source_branch = self._canonical_branch(clone_path)
        source_revision, index_content = self._capture_candidate(
            clone_path,
            _remote_tracking_ref(source_branch),
        )
        return PreparedIndexSource(
            source=source,
            source_type=IndexSourceType.GIT_URL,
            repository_path=str(clone_path),
            source_revision=source_revision,
            source_branch=source_branch,
            index_content=index_content,
            source_cache_path=str(clone_path),
        )

    def refresh_source(
        self,
        *,
        source: str,
        source_cache_path: str | None,
        cache_root: str | None,
        source_branch: str | None = None,
        registry_path: str | None = None,
    ) -> PreparedIndexSource:
        """Refresh a remembered source for update-index."""
        source_path = Path(source).expanduser()
        if source_cache_path is None and source_path.exists():
            if source_branch is None:
                msg = "registered local Git index has no canonical source branch"
                raise IndexSourceError(msg)
            return self._local_source(source_path, source_branch=source_branch)
        if source_branch is None:
            msg = "registered Git URL index has no canonical source branch"
            raise IndexSourceError(msg)
        _require_safe_git_url(source)
        clone_path = (
            Path(source_cache_path).expanduser()
            if source_cache_path
            else _managed_clone_path(source, cache_root, registry_path)
        )
        if clone_path.exists():
            self._refresh_clone(clone_path, source_branch)
        else:
            self._clone_source(source, clone_path)
        source_revision, index_content = self._capture_candidate(
            clone_path,
            _remote_tracking_ref(source_branch),
        )
        return PreparedIndexSource(
            source=source,
            source_type=IndexSourceType.GIT_URL,
            repository_path=str(clone_path),
            source_revision=source_revision,
            source_branch=source_branch,
            index_content=index_content,
            source_cache_path=str(clone_path),
        )

    def _local_source(
        self,
        source_path: Path,
        *,
        source_branch: str | None = None,
    ) -> PreparedIndexSource:
        if not (source_path / ".git").exists():
            msg = "local index source must be a Git repository"
            raise IndexSourceError(msg)
        status = self._run(
            [
                "git",
                "-C",
                str(source_path),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ],
        )
        if status.stdout:
            msg = "local index source has uncommitted changes; commit or discard them before registration"
            raise IndexSourceError(msg)
        selected_branch = source_branch or self._local_branch(source_path)
        source_revision, index_content = self._capture_candidate(
            source_path,
            selected_branch,
        )
        return PreparedIndexSource(
            source=str(source_path),
            source_type=IndexSourceType.LOCAL_GIT_REPO,
            repository_path=str(source_path),
            source_revision=source_revision,
            source_branch=selected_branch,
            index_content=index_content,
        )

    def _clone_source(self, source: str, clone_path: Path) -> None:
        clone_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["git", "clone", "--", source, str(clone_path)])

    def _refresh_clone(self, clone_path: Path, source_branch: str) -> None:
        branch_name = source_branch.removeprefix("refs/heads/")
        self._run(
            [
                "git",
                "-C",
                str(clone_path),
                "fetch",
                "--prune",
                "--tags",
                "origin",
                f"+{source_branch}:refs/remotes/origin/{branch_name}",
            ],
        )

    def _capture_candidate(
        self,
        repository_path: Path,
        revision: str,
    ) -> tuple[str, bytes]:
        result = self._run(
            [
                "git",
                "-C",
                str(repository_path),
                "rev-parse",
                "--verify",
                f"{revision}^{{commit}}",
            ],
        )
        try:
            source_revision = result.stdout.decode("ascii").strip()
        except UnicodeDecodeError as err:
            msg = "git source revision is not a valid object ID"
            raise IndexSourceError(msg) from err
        index_result = self._run(
            [
                "git",
                "-C",
                str(repository_path),
                "show",
                f"{source_revision}:ritebook-index.json",
            ],
        )
        if not index_result.stdout:
            msg = "committed ritebook-index.json is empty"
            raise IndexSourceError(msg)
        return source_revision, index_result.stdout

    def _canonical_branch(self, repository_path: Path) -> str:
        result = self._run(
            [
                "git",
                "-C",
                str(repository_path),
                "symbolic-ref",
                "--quiet",
                "refs/remotes/origin/HEAD",
            ],
        )
        try:
            remote_reference = result.stdout.decode("utf-8").strip()
        except UnicodeDecodeError as err:
            msg = "git source default branch is invalid"
            raise IndexSourceError(msg) from err
        prefix = "refs/remotes/origin/"
        if not remote_reference.startswith(prefix):
            msg = "git source default branch is unavailable"
            raise IndexSourceError(msg)
        branch_name = remote_reference.removeprefix(prefix)
        if not branch_name:
            msg = "git source default branch is unavailable"
            raise IndexSourceError(msg)
        return f"refs/heads/{branch_name}"

    def _local_branch(self, repository_path: Path) -> str:
        result = self._run(
            [
                "git",
                "-C",
                str(repository_path),
                "symbolic-ref",
                "--quiet",
                "HEAD",
            ],
        )
        try:
            branch = result.stdout.decode("utf-8").strip()
        except UnicodeDecodeError as err:
            msg = "local index source branch is invalid"
            raise IndexSourceError(msg) from err
        if not branch.startswith("refs/heads/"):
            msg = "local index source must have a checked-out branch"
            raise IndexSourceError(msg)
        return branch

    def _run(self, command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
        result = self._runner(command)
        if result.returncode != 0:
            msg = "git source operation failed"
            raise IndexSourceError(msg)
        return result


def _managed_clone_path(
    source: str,
    cache_root: str | None,
    registry_path: str | None,
) -> Path:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return registry_cache_root(cache_root, registry_path) / "git" / digest


def _remote_tracking_ref(source_branch: str) -> str:
    branch_name = source_branch.removeprefix("refs/heads/")
    return f"refs/remotes/origin/{branch_name}"


def _require_safe_git_url(source: str) -> None:
    try:
        require_safe_persisted_source(source, IndexSourceType.GIT_URL.value)
    except ValueError as err:
        raise IndexSourceError(str(err)) from err


def _run_git(command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
    )
