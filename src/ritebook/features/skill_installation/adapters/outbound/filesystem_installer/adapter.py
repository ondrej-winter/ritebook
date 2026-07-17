"""Safely copy cached skill directories into explicit target paths."""

from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.errors import (
    ExistingInstallTargetError,
    UnsafeInstallPathError,
)

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        ResolvedSkillSource,
    )


class FilesystemSkillInstallerAdapter:
    """Filesystem-backed adapter for installing a whole skill directory."""

    def install(
        self,
        *,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
        target: str,
        force: bool,
    ) -> None:
        """Copy a validated skill directory to a validated target path."""
        repository_path = Path(source.repository_path).expanduser().resolve()
        source_directory = _resolve_source_directory(repository_path, skill)
        target_path = _safe_target_path(target)

        if target_path.exists() or target_path.is_symlink():
            if target_path.is_symlink():
                msg = f"target {target} is a symlink and cannot be replaced safely"
                raise UnsafeInstallPathError(msg)
            if not force:
                raise ExistingInstallTargetError(target)
            _remove_target(target_path)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_directory, target_path, symlinks=False)


def _resolve_source_directory(
    repository_path: Path,
    skill: InstallableSkill,
) -> Path:
    source_root = _safe_relative_posix_path(
        skill.source_root,
        field_name="skill source root",
    )
    skill_path = _safe_relative_posix_path(skill.path, field_name="skill path")
    skill_file = _safe_relative_posix_path(skill.skill_file, field_name="skill file")
    if not _is_relative_to(skill_file, skill_path):
        msg = f"skill file {skill.skill_file} is outside skill path {skill.path}"
        raise UnsafeInstallPathError(msg)

    raw_source_directory = (
        repository_path
        / Path(*source_root.parts)
        / Path(
            *skill_path.parts,
        )
    )
    raw_source_file = (
        repository_path
        / Path(*source_root.parts)
        / Path(
            *skill_file.parts,
        )
    )
    if raw_source_directory.is_symlink() or raw_source_file.is_symlink():
        msg = "skill source paths must not be symlinks"
        raise UnsafeInstallPathError(msg)

    source_directory = raw_source_directory.resolve()
    source_file = raw_source_file.resolve()
    _require_contained(source_directory, repository_path, label="skill path")
    _require_contained(source_file, repository_path, label="skill file")
    _require_contained(source_file, source_directory, label="skill file")

    if not source_directory.is_dir():
        msg = f"skill source directory does not exist: {skill.path}"
        raise UnsafeInstallPathError(msg)
    if not source_file.is_file():
        msg = f"skill file does not exist: {skill.skill_file}"
        raise UnsafeInstallPathError(msg)
    if _contains_symlink(source_directory):
        msg = "skill source directory contains symlinks and cannot be copied safely"
        raise UnsafeInstallPathError(msg)
    return source_directory


def _safe_relative_posix_path(value: str, *, field_name: str) -> PurePosixPath:
    if "\\" in value:
        msg = f"{field_name} must use POSIX-style relative paths"
        raise UnsafeInstallPathError(msg)
    path = PurePosixPath(value)
    if path.is_absolute() or not value or any(part == ".." for part in path.parts):
        msg = f"{field_name} must be a safe relative path"
        raise UnsafeInstallPathError(msg)
    return path


def _safe_target_path(value: str) -> Path:
    target_path = Path(value).expanduser()
    if not value or not str(target_path):
        msg = "target path must not be empty"
        raise UnsafeInstallPathError(msg)
    if target_path.is_symlink():
        msg = f"target {value} is a symlink and cannot be replaced safely"
        raise UnsafeInstallPathError(msg)
    resolved = target_path.resolve(strict=False)
    home = Path.home().resolve()
    cwd = Path.cwd().resolve()
    if resolved == Path(resolved.anchor):
        msg = f"target {value} resolves to filesystem root"
        raise UnsafeInstallPathError(msg)
    if resolved == home:
        msg = f"target {value} resolves to the home directory"
        raise UnsafeInstallPathError(msg)
    if resolved == cwd:
        msg = f"target {value} resolves to the current working directory"
        raise UnsafeInstallPathError(msg)
    return resolved


def _remove_target(target_path: Path) -> None:
    if target_path.is_dir():
        shutil.rmtree(target_path)
        return
    target_path.unlink()


def _require_contained(path: Path, base: Path, *, label: str) -> None:
    if not path.is_relative_to(base):
        msg = f"{label} escapes source repository"
        raise UnsafeInstallPathError(msg)


def _is_relative_to(path: PurePosixPath, base: PurePosixPath) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def _contains_symlink(path: Path) -> bool:
    return any(child.is_symlink() for child in path.rglob("*"))
