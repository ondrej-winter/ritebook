"""Safely copy cached skill directories into explicit target paths."""

from __future__ import annotations

import os
import secrets
import shutil
import stat
from contextlib import suppress
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.adapters.outbound.safe_filesystem import (
    absolute_path,
    entry_metadata,
    open_verified_directory,
    remove_entry,
    remove_path,
    require_directory_identity,
    sync_directory_descriptor,
)
from ritebook.features.skill_installation.adapters.outbound.tree_digest import (
    canonical_tree_digest,
    canonical_tree_digest_at,
)
from ritebook.features.skill_installation.application.dtos import (
    PlannedInstallTarget,
    StagedSkillTree,
    TargetInspection,
)
from ritebook.features.skill_installation.application.errors import (
    InstallationPersistenceError,
    UnsafeInstallPathError,
)

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        ResolvedSkillSource,
    )


class FilesystemSkillInstallerAdapter:
    """Filesystem-backed adapter for installing a whole skill directory."""

    def plan_target(self, target: str) -> PlannedInstallTarget:
        """Resolve and validate a target without mutating the filesystem."""
        return PlannedInstallTarget(
            requested_target=target,
            canonical_target=str(_safe_target_path(target)),
        )

    def tree_digest(self, target: str) -> str:
        """Return a canonical digest for one symlink-free regular file tree."""
        return canonical_tree_digest(Path(target).expanduser())

    def inspect_target(self, target: PlannedInstallTarget) -> TargetInspection:
        """Inspect one planned target without following symlinks or mutating it."""
        target_path = _safe_target_path(target.canonical_target)
        if not (target_path.exists() or target_path.is_symlink()):
            return TargetInspection(
                canonical_target=str(target_path),
                exists=False,
            )
        if target_path.is_symlink():
            msg = f"target {target.requested_target} is a symlink and is unsafe"
            raise UnsafeInstallPathError(msg)
        digest = canonical_tree_digest(target_path) if target_path.is_dir() else None
        return TargetInspection(
            canonical_target=str(target_path),
            exists=True,
            installed_tree_digest=digest,
        )

    def stage(
        self,
        *,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
        target: PlannedInstallTarget,
    ) -> StagedSkillTree:
        """Stage and hash a complete candidate beside its canonical target."""
        repository_path = Path(source.repository_path).expanduser().resolve()
        source_directory = _resolve_source_directory(repository_path, skill)
        target_path = _safe_target_path(target.canonical_target)
        _require_no_source_target_overlap(source_directory, target_path)
        with (
            open_verified_directory(
                source_directory,
                create=False,
                label=f"skill source directory {source_directory}",
            ) as source_fd,
            open_verified_directory(
                target_path.parent,
                create=True,
                label=f"target parent for {target_path}",
            ) as target_parent_fd,
        ):
            cleanup_name = _create_staging_directory(
                target_parent_fd,
                target_name=target_path.name,
            )
            cleanup_path = target_path.parent / cleanup_name
            try:
                cleanup_fd = _open_child_directory(target_parent_fd, cleanup_name)
                try:
                    os.mkdir("candidate", dir_fd=cleanup_fd)
                    staged_fd = _open_child_directory(cleanup_fd, "candidate")
                    try:
                        _copy_directory(source_fd, staged_fd)
                    finally:
                        os.close(staged_fd)
                    digest = canonical_tree_digest_at(
                        cleanup_fd,
                        "candidate",
                        display_path=cleanup_path / "candidate",
                    )
                finally:
                    os.close(cleanup_fd)
                require_directory_identity(target_path.parent, target_parent_fd)
            except BaseException as err:
                metadata = entry_metadata(target_parent_fd, cleanup_name)
                if metadata is not None:
                    with suppress(OSError):
                        remove_entry(target_parent_fd, cleanup_name, metadata)
                        sync_directory_descriptor(target_parent_fd)
                if isinstance(err, OSError):
                    msg = f"unable to stage replacement for target {target_path}"
                    raise InstallationPersistenceError(msg) from err
                raise
        staged_path = cleanup_path / "candidate"
        return StagedSkillTree(
            staged_path=str(staged_path),
            cleanup_path=str(cleanup_path),
            installed_tree_digest=digest,
        )

    def cleanup_staged(self, staged: StagedSkillTree) -> None:
        """Remove one staging root after commit, rollback, or a skipped candidate."""
        try:
            remove_path(Path(staged.cleanup_path), missing_parent_ok=False)
        except (OSError, UnsafeInstallPathError) as err:
            msg = f"unable to remove staged skill data: {staged.cleanup_path}"
            raise InstallationPersistenceError(msg) from err


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
    _require_no_symlink_components(target_path, value)
    absolute = absolute_path(target_path)
    home = absolute_path(Path.home())
    cwd = absolute_path(Path.cwd())
    if absolute == Path(absolute.anchor):
        msg = f"target {value} resolves to filesystem root"
        raise UnsafeInstallPathError(msg)
    if absolute == home:
        msg = f"target {value} resolves to the home directory"
        raise UnsafeInstallPathError(msg)
    if absolute == cwd:
        msg = f"target {value} resolves to the current working directory"
        raise UnsafeInstallPathError(msg)
    return absolute


def _require_no_symlink_components(target_path: Path, value: str) -> None:
    absolute_target = target_path.absolute()
    for path in (absolute_target, *absolute_target.parents):
        if path.is_symlink():
            msg = f"target {value} contains a symlink path and cannot be used safely"
            raise UnsafeInstallPathError(msg)


def _create_staging_directory(parent_fd: int, *, target_name: str) -> str:
    for _attempt in range(100):
        name = f".{target_name}.ritebook-stage-{secrets.token_hex(8)}"
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        return name
    msg = f"unable to allocate staging directory for target {target_name}"
    raise InstallationPersistenceError(msg)


def _open_child_directory(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except OSError as err:
        msg = f"staging directory changed and cannot be opened safely: {name}"
        raise UnsafeInstallPathError(msg) from err


def _copy_directory(source_fd: int, destination_fd: int) -> None:
    try:
        names = sorted(entry.name for entry in os.scandir(source_fd))
    except OSError as err:
        msg = "skill source directory cannot be enumerated safely"
        raise UnsafeInstallPathError(msg) from err

    for name in names:
        try:
            metadata = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
        except OSError as err:
            msg = f"skill source entry cannot be inspected safely: {name}"
            raise UnsafeInstallPathError(msg) from err
        if stat.S_ISDIR(metadata.st_mode):
            _copy_child_directory(
                source_fd,
                destination_fd,
                name=name,
                mode=stat.S_IMODE(metadata.st_mode),
            )
            continue
        if stat.S_ISREG(metadata.st_mode):
            _copy_regular_file(
                source_fd,
                destination_fd,
                name=name,
                mode=stat.S_IMODE(metadata.st_mode),
            )
            continue
        msg = f"skill source directory may contain only regular files and directories: {name}"
        raise UnsafeInstallPathError(msg)


def _copy_child_directory(
    source_parent_fd: int,
    destination_parent_fd: int,
    *,
    name: str,
    mode: int,
) -> None:
    source_child_fd = _open_child_directory(source_parent_fd, name)
    try:
        os.mkdir(name, mode=mode, dir_fd=destination_parent_fd)
        destination_child_fd = _open_child_directory(destination_parent_fd, name)
        try:
            os.fchmod(destination_child_fd, mode)
            _copy_directory(source_child_fd, destination_child_fd)
            sync_directory_descriptor(destination_child_fd)
        finally:
            os.close(destination_child_fd)
    finally:
        os.close(source_child_fd)


def _copy_regular_file(
    source_parent_fd: int,
    destination_parent_fd: int,
    *,
    name: str,
    mode: int,
) -> None:
    source_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    destination_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        source_fd = os.open(name, source_flags, dir_fd=source_parent_fd)
    except OSError as err:
        msg = f"skill source file changed and cannot be copied safely: {name}"
        raise UnsafeInstallPathError(msg) from err
    try:
        if not stat.S_ISREG(os.fstat(source_fd).st_mode):
            msg = f"skill source file changed type and cannot be copied safely: {name}"
            raise UnsafeInstallPathError(msg)
        destination_fd = os.open(
            name,
            destination_flags,
            mode,
            dir_fd=destination_parent_fd,
        )
        try:
            with (
                os.fdopen(os.dup(source_fd), "rb") as source_file,
                os.fdopen(os.dup(destination_fd), "wb") as destination_file,
            ):
                shutil.copyfileobj(source_file, destination_file)
                destination_file.flush()
                os.fsync(destination_file.fileno())
            os.fchmod(destination_fd, mode)
        finally:
            os.close(destination_fd)
    finally:
        os.close(source_fd)


def _require_no_source_target_overlap(
    source_directory: Path,
    target_path: Path,
) -> None:
    if source_directory.is_relative_to(target_path) or target_path.is_relative_to(
        source_directory,
    ):
        msg = "unsafe source-target overlap; choose a target outside the source skill"
        raise UnsafeInstallPathError(msg)


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
