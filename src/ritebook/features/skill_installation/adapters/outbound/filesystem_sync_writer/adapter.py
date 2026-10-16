"""Staged per-target replacement and atomic lockfile writes without recovery."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.adapters.outbound.filesystem_installer import FilesystemSkillInstallerAdapter
from ritebook.features.skill_installation.adapters.outbound.safe_filesystem import (
    absolute_path,
    entry_metadata,
    open_verified_directory,
    remove_entry,
    rename_entry,
    require_directory_identity,
    sync_directory_descriptor,
)
from ritebook.features.skill_installation.adapters.outbound.tree_digest import canonical_tree_digest_at
from ritebook.features.skill_installation.application.errors import InstallationPersistenceError, UnsafeInstallPathError

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import GeneratedStateFile


class FilesystemSyncWriterAdapter:
    """Write sync results without operation locks, journals, or batch rollback."""

    def replace_tree(
        self,
        *,
        staged_path: str,
        target_path: str,
        expected_digest: str | None,
    ) -> None:
        """Place a fully staged tree after revalidating the target."""
        staged = absolute_path(Path(staged_path))
        target = Path(FilesystemSkillInstallerAdapter().plan_target(target_path).canonical_target)
        if staged == target or staged in target.parents or target in staged.parents:
            msg = "staged and target trees must not overlap"
            raise UnsafeInstallPathError(msg)
        try:
            with (
                open_verified_directory(target.parent, create=True, label=f"target parent for {target}") as target_fd,
                open_verified_directory(staged.parent, create=False, label=f"staging parent for {staged}") as staged_fd,
            ):
                canonical_tree_digest_at(staged_fd, staged.name, display_path=staged)
                _revalidate_target(target, target_fd, expected_digest)
                require_directory_identity(target.parent, target_fd)
                require_directory_identity(staged.parent, staged_fd)
                _place_tree(staged, staged_fd, target, target_fd, had_prior=expected_digest is not None)
        except OSError as err:
            msg = f"unable to replace installation target: {target}"
            raise InstallationPersistenceError(msg) from err

    def write_lockfile(self, candidate: GeneratedStateFile) -> None:
        """Atomically replace a complete lockfile document."""
        path = absolute_path(Path(candidate.path))
        try:
            with open_verified_directory(path.parent, create=True, label=f"lockfile parent for {path}") as parent_fd:
                _write_lockfile(path, parent_fd, candidate)
        except OSError as err:
            msg = f"unable to write sync lockfile: {path}"
            raise InstallationPersistenceError(msg) from err


def _revalidate_target(target: Path, parent_fd: int, expected: str | None) -> None:
    exists = entry_metadata(parent_fd, target.name) is not None
    if expected is None:
        if exists:
            msg = f"target {target} exists without an expected tree digest"
            raise UnsafeInstallPathError(msg)
        return
    if not exists:
        msg = f"inspected target is missing: {target}"
        raise InstallationPersistenceError(msg)
    if canonical_tree_digest_at(parent_fd, target.name, display_path=target) != expected:
        msg = f"installation target changed after inspection: {target}"
        raise InstallationPersistenceError(msg)


def _place_tree(staged: Path, staged_fd: int, target: Path, target_fd: int, *, had_prior: bool) -> None:
    backup = target.with_name(f".{target.name}.ritebook-{secrets.token_hex(16)}.previous")
    moved_prior = False
    placed = False
    try:
        if had_prior:
            rename_entry(target_fd, target.name, target_fd, backup.name)
            moved_prior = True
            sync_directory_descriptor(target_fd)
        rename_entry(staged_fd, staged.name, target_fd, target.name)
        placed = True
        sync_directory_descriptor(target_fd)
        sync_directory_descriptor(staged_fd)
        require_directory_identity(target.parent, target_fd)
        require_directory_identity(staged.parent, staged_fd)
    except (OSError, UnsafeInstallPathError) as err:
        if moved_prior and not placed:
            try:
                require_directory_identity(target.parent, target_fd)
                rename_entry(target_fd, backup.name, target_fd, target.name)
                sync_directory_descriptor(target_fd)
            except (OSError, UnsafeInstallPathError) as restore_error:
                msg = f"unable to place target {target}; restoration failed; prior tree retained at {backup}"
                raise InstallationPersistenceError(msg) from restore_error
        if placed and moved_prior:
            try:
                _remove_backup(backup, target_fd)
            except (OSError, UnsafeInstallPathError) as cleanup_error:
                msg = f"target {target} was placed but finalization failed; prior tree retained at {backup}"
                raise InstallationPersistenceError(msg) from cleanup_error
        msg = f"unable to replace installation target: {target}"
        raise InstallationPersistenceError(msg) from err
    # Placement succeeded: cleanup failure must never restore the old tree.
    if moved_prior:
        try:
            _remove_backup(backup, target_fd)
        except (OSError, UnsafeInstallPathError) as err:
            msg = f"target {target} was placed; unable to clean up prior tree retained at {backup}"
            raise InstallationPersistenceError(msg) from err


def _remove_backup(backup: Path, parent_fd: int) -> None:
    require_directory_identity(backup.parent, parent_fd)
    metadata = entry_metadata(parent_fd, backup.name)
    if metadata is not None:
        remove_entry(parent_fd, backup.name, metadata)
        sync_directory_descriptor(parent_fd)


def _write_lockfile(path: Path, parent_fd: int, candidate: GeneratedStateFile) -> None:
    temporary_name = f".{path.name}.{secrets.token_hex(16)}.tmp"
    temporary = path.with_name(temporary_name)
    # Create relative to the verified directory so an ancestor swap cannot redirect I/O.
    descriptor = os.open(
        temporary_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600 if candidate.private else 0o644,
        dir_fd=parent_fd,
    )
    failure: BaseException | None = None
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(candidate.content)
            file.flush()
            os.fsync(file.fileno())
        require_directory_identity(path.parent, parent_fd)
        rename_entry(parent_fd, temporary_name, parent_fd, path.name)
        sync_directory_descriptor(parent_fd)
        require_directory_identity(path.parent, parent_fd)
    except BaseException as err:
        failure = err
        raise
    finally:
        try:
            metadata = entry_metadata(parent_fd, temporary_name)
            if metadata is not None:
                remove_entry(parent_fd, temporary_name, metadata)
                sync_directory_descriptor(parent_fd)
        except (OSError, UnsafeInstallPathError) as err:
            primary = "lockfile write failed; " if failure is not None else "lockfile may already be replaced; "
            msg = f"{primary}temporary lockfile cleanup failed; inspect {temporary}"
            if failure is not None and not isinstance(failure, Exception):
                failure.add_note(msg)
                raise failure from err
            raise InstallationPersistenceError(msg) from (failure or err)
