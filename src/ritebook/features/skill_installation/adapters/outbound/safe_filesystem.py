"""Descriptor-bound filesystem primitives for installation mutation boundaries."""

from __future__ import annotations

import os
import shutil
import stat
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.errors import (
    UnsafeInstallPathError,
)

if TYPE_CHECKING:
    from collections.abc import Generator


def absolute_path(path: Path) -> Path:
    """Return a lexical absolute path without resolving symlinks."""
    # Path.resolve() would follow symlinks before descriptor validation.
    return Path(os.path.abspath(path.expanduser()))  # noqa: PTH100


@contextmanager
def open_verified_directory(
    path: Path,
    *,
    create: bool,
    label: str,
) -> Generator[int]:
    """Open every directory component without following symlinks."""
    absolute = absolute_path(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(absolute.anchor, flags)
        try:
            for part in absolute.parts[1:]:
                try:
                    child_descriptor = os.open(part, flags, dir_fd=descriptor)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(part, dir_fd=descriptor)
                    child_descriptor = os.open(part, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child_descriptor
        except BaseException:
            os.close(descriptor)
            raise
    except OSError as err:
        msg = f"{label} contains a symlink or is not a directory and cannot be used safely"
        raise UnsafeInstallPathError(msg) from err

    try:
        yield descriptor
    finally:
        os.close(descriptor)


def require_directory_identity(path: Path, descriptor: int) -> None:
    """Fail when a stable directory descriptor no longer matches its path."""
    with open_verified_directory(
        path,
        create=False,
        label=f"directory {path}",
    ) as current_descriptor:
        if not same_directory(descriptor, current_descriptor):
            msg = f"directory {path} changed and cannot be used safely"
            raise UnsafeInstallPathError(msg)


def same_directory(first_fd: int, second_fd: int) -> bool:
    """Return whether two descriptors refer to the same directory object."""
    first = os.fstat(first_fd)
    second = os.fstat(second_fd)
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def entry_metadata(parent_fd: int, name: str) -> os.stat_result | None:
    """Inspect one child entry without following a symlink."""
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def rename_entry(
    source_parent_fd: int,
    source_name: str,
    destination_parent_fd: int,
    destination_name: str,
) -> None:
    """Rename one entry relative to stable source and destination descriptors."""
    os.rename(
        source_name,
        destination_name,
        src_dir_fd=source_parent_fd,
        dst_dir_fd=destination_parent_fd,
    )


def remove_entry(parent_fd: int, name: str, metadata: os.stat_result) -> None:
    """Remove one inspected child without following it through a path lookup."""
    if stat.S_ISDIR(metadata.st_mode):
        shutil.rmtree(name, dir_fd=parent_fd)
        return
    os.unlink(name, dir_fd=parent_fd)


def sync_directory_descriptor(descriptor: int) -> None:
    """Synchronize one directory descriptor where the platform supports it."""
    with suppress(OSError):
        os.fsync(descriptor)


def remove_path(path: Path, *, missing_parent_ok: bool = True) -> None:
    """Remove one path through a verified parent descriptor without following links."""
    absolute = absolute_path(path)
    if absolute == Path(absolute.anchor):
        msg = f"refusing to remove filesystem root: {path}"
        raise UnsafeInstallPathError(msg)
    try:
        with open_verified_directory(
            absolute.parent,
            create=False,
            label=f"parent for {absolute}",
        ) as parent_fd:
            metadata = entry_metadata(parent_fd, absolute.name)
            if metadata is None:
                return
            require_directory_identity(absolute.parent, parent_fd)
            remove_entry(parent_fd, absolute.name, metadata)
            sync_directory_descriptor(parent_fd)
    except UnsafeInstallPathError as err:
        if missing_parent_ok and isinstance(err.__cause__, FileNotFoundError):
            return
        raise
