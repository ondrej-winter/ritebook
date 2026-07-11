"""Resolve registered installation source repositories without mutating Git."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from ritebook.features.skill_installation.application.dtos import (
    RegisteredSkillIndex,
    ResolvedSkillSource,
)
from ritebook.features.skill_installation.application.errors import (
    SkillSourceResolutionError,
)

GIT_URL_SOURCE_TYPE = "git_url"
LOCAL_GIT_REPO_SOURCE_TYPE = "local_git_repo"
GitRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class SourceRepositoryAdapter:
    """Resolve registered source repository paths and optional revisions."""

    def __init__(self, runner: GitRunner | None = None) -> None:
        """Initialize the adapter with an injectable read-only Git runner."""
        self._runner = runner or _run_git

    def resolve_source(self, index: RegisteredSkillIndex) -> ResolvedSkillSource:
        """Resolve source metadata for a registered installation index."""
        repository_path = self._repository_path(index)
        source_revision = self._read_revision(repository_path)
        return ResolvedSkillSource(
            source=index.source,
            source_type=index.source_type,
            repository_path=str(repository_path),
            source_revision=source_revision,
        )

    def _repository_path(self, index: RegisteredSkillIndex) -> Path:
        if index.source_type == GIT_URL_SOURCE_TYPE:
            if index.source_cache_path is None:
                msg = f"registered Git URL index has no source cache path: {index.name}"
                raise SkillSourceResolutionError(msg)
            return _existing_path(
                index.source_cache_path,
                missing_message=f"source repository cache does not exist: {index.name}",
            )
        if index.source_type == LOCAL_GIT_REPO_SOURCE_TYPE:
            return _existing_path(
                index.source,
                missing_message=f"local source repository does not exist: {index.name}",
            )
        msg = f"unsupported source type for installation: {index.source_type}"
        raise SkillSourceResolutionError(msg)

    def _read_revision(self, repository_path: Path) -> str | None:
        result = self._runner(
            ["git", "-C", str(repository_path), "rev-parse", "HEAD"],
        )
        if result.returncode != 0:
            return None
        revision = result.stdout.strip()
        return revision or None


def _existing_path(value: str, *, missing_message: str) -> Path:
    path = Path(value).expanduser()
    if not path.exists():
        raise SkillSourceResolutionError(missing_message)
    return path


def _run_git(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
        text=True,
    )
