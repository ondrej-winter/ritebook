"""Verify and materialize commit-bound installation sources without mutating Git."""

from __future__ import annotations

import hashlib
import io
import subprocess
import tarfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from ritebook.features.skill_installation.application.dtos import (
    RegisteredSkillIndex,
    ResolvedSkillSource,
)
from ritebook.features.skill_installation.application.errors import (
    SkillSourceResolutionError,
)

GIT_URL_SOURCE_TYPE = "git_url"
LOCAL_GIT_REPO_SOURCE_TYPE = "local_git_repo"
GitRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[bytes]]
SnapshotExporter = Callable[[Path, str, Path], None]


class SourceRepositoryAdapter:
    """Verify provenance and expose a temporary snapshot of the bound commit."""

    def __init__(
        self,
        runner: GitRunner | None = None,
        *,
        exporter: SnapshotExporter | None = None,
    ) -> None:
        """Initialize injectable read-only Git operations."""
        self._runner = runner or _run_git
        self._exporter = exporter or _export_git_snapshot

    @contextmanager
    def open_source(
        self,
        index: RegisteredSkillIndex,
    ) -> Iterator[ResolvedSkillSource]:
        """Verify both index copies and yield the exact bound commit snapshot."""
        self._verify_cached_index(index)
        repository_path = self._repository_path(index)
        self._require_bound_commit(repository_path, index)
        self._verify_committed_index(repository_path, index)

        try:
            with TemporaryDirectory(prefix="ritebook-source-") as temporary_path:
                snapshot_path = Path(temporary_path)
                self._exporter(repository_path, index.source_revision, snapshot_path)
                yield ResolvedSkillSource(
                    source=index.source,
                    source_type=index.source_type,
                    repository_path=str(snapshot_path),
                    source_revision=index.source_revision,
                )
        except SkillSourceResolutionError:
            raise
        except (OSError, subprocess.SubprocessError, tarfile.TarError) as err:
            msg = "unable to materialize the bound source commit"
            raise SkillSourceResolutionError(msg) from err

    def _verify_cached_index(self, index: RegisteredSkillIndex) -> None:
        try:
            content = Path(index.cached_index_path).read_bytes()
        except OSError as err:
            msg = "unable to read the cached index; run update-index to regenerate it"
            raise SkillSourceResolutionError(msg) from err
        if _digest(content) != index.index_digest:
            msg = "cached index digest mismatch; run update-index to regenerate it"
            raise SkillSourceResolutionError(msg)

    def _repository_path(self, index: RegisteredSkillIndex) -> Path:
        if index.source_type == GIT_URL_SOURCE_TYPE:
            if index.source_cache_path is None:
                msg = f"registered Git URL index has no source cache path: {index.name}"
                raise SkillSourceResolutionError(msg)
            return _existing_repository(
                index.source_cache_path,
                message="source repository cache is unavailable; run update-index",
            )
        if index.source_type == LOCAL_GIT_REPO_SOURCE_TYPE:
            return _existing_repository(
                index.source,
                message=(
                    "local source repository is unavailable; restore it or run "
                    "update-index to select a new validated source"
                ),
            )
        msg = f"unsupported source type for installation: {index.source_type}"
        raise SkillSourceResolutionError(msg)

    def _require_bound_commit(
        self,
        repository_path: Path,
        index: RegisteredSkillIndex,
    ) -> None:
        result = self._runner(
            [
                "git",
                "-C",
                str(repository_path),
                "cat-file",
                "-e",
                f"{index.source_revision}^{{commit}}",
            ],
        )
        if result.returncode != 0:
            msg = "bound source commit is unavailable; restore it or run update-index"
            raise SkillSourceResolutionError(msg)

    def _verify_committed_index(
        self,
        repository_path: Path,
        index: RegisteredSkillIndex,
    ) -> None:
        result = self._runner(
            [
                "git",
                "-C",
                str(repository_path),
                "show",
                f"{index.source_revision}:ritebook-index.json",
            ],
        )
        if result.returncode != 0:
            msg = "bound commit index is unavailable; restore it or run update-index"
            raise SkillSourceResolutionError(msg)
        if _digest(result.stdout) != index.index_digest:
            msg = (
                "bound commit index mismatch; run update-index to revalidate the source"
            )
            raise SkillSourceResolutionError(msg)


def _existing_repository(value: str, *, message: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_dir():
        raise SkillSourceResolutionError(message)
    return path


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _export_git_snapshot(repository: Path, revision: str, destination: Path) -> None:
    result = _run_git(["git", "-C", str(repository), "archive", revision])
    if result.returncode != 0:
        msg = "unable to archive the bound source commit"
        raise SkillSourceResolutionError(msg)
    try:
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            archive.extractall(destination, filter="data")
    except (OSError, tarfile.TarError) as err:
        msg = "unable to extract the bound source commit"
        raise SkillSourceResolutionError(msg) from err


def _run_git(command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
    )
