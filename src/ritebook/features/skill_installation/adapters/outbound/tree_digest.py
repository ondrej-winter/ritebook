"""Canonical content identity for managed installed skill trees."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Protocol

from ritebook.features.skill_installation.application.errors import (
    UnsafeInstallPathError,
)


class _HashWriter(Protocol):
    def update(self, data: bytes, /) -> None:
        """Add bytes to the digest input."""


def canonical_tree_digest(root: Path) -> str:
    """Return a deterministic digest for a symlink-free regular file tree."""
    # Normalize lexically; Path.resolve() would follow symlinks before validation.
    root = Path(os.path.abspath(root.expanduser()))  # noqa: PTH100
    try:
        root_fd = _open_directory_no_follow(root)
    except OSError as err:
        msg = f"managed skill tree is not a readable directory: {root}"
        raise UnsafeInstallPathError(msg) from err
    try:
        return _canonical_tree_digest_from_descriptor(root_fd)
    finally:
        os.close(root_fd)


def canonical_tree_digest_at(
    parent_fd: int,
    name: str,
    *,
    display_path: Path,
) -> str:
    """Hash one child directory relative to an already verified parent descriptor."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        root_fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as err:
        msg = f"managed skill tree is not a readable directory: {display_path}"
        raise UnsafeInstallPathError(msg) from err
    try:
        return _canonical_tree_digest_from_descriptor(root_fd)
    finally:
        os.close(root_fd)


def _canonical_tree_digest_from_descriptor(root_fd: int) -> str:
    digest = hashlib.sha256()
    digest.update(b"ritebook-tree-v1\0")
    _hash_directory(digest, root_fd, relative_parent=PurePosixPath())
    return f"sha256:{digest.hexdigest()}"


def _open_directory_no_follow(path: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            child_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child_descriptor
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _hash_directory(
    digest: _HashWriter,
    directory_fd: int,
    *,
    relative_parent: PurePosixPath,
) -> None:
    try:
        names = sorted(entry.name for entry in os.scandir(directory_fd))
    except OSError as err:
        msg = "managed skill tree cannot be enumerated safely"
        raise UnsafeInstallPathError(msg) from err

    for name in names:
        relative_path = relative_parent / name
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as err:
            msg = f"managed skill tree entry cannot be inspected: {relative_path}"
            raise UnsafeInstallPathError(msg) from err

        if stat.S_ISDIR(metadata.st_mode):
            _hash_record(digest, b"D", relative_path.as_posix().encode("utf-8"))
            child_flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            try:
                child_fd = os.open(name, child_flags, dir_fd=directory_fd)
            except OSError as err:
                msg = f"managed skill tree directory changed unsafely: {relative_path}"
                raise UnsafeInstallPathError(msg) from err
            try:
                _hash_directory(
                    digest,
                    child_fd,
                    relative_parent=relative_path,
                )
            finally:
                os.close(child_fd)
            continue

        if stat.S_ISREG(metadata.st_mode):
            _hash_regular_file(
                digest,
                directory_fd,
                name=name,
                relative_path=relative_path,
            )
            continue

        msg = (
            "managed skill trees may contain only regular files and directories: "
            f"{relative_path}"
        )
        raise UnsafeInstallPathError(msg)


def _hash_regular_file(
    digest: _HashWriter,
    directory_fd: int,
    *,
    name: str,
    relative_path: PurePosixPath,
) -> None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_fd = os.open(name, flags, dir_fd=directory_fd)
    except OSError as err:
        msg = f"managed skill tree file changed unsafely: {relative_path}"
        raise UnsafeInstallPathError(msg) from err
    try:
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            msg = (
                "managed skill trees may contain only regular files and directories: "
                f"{relative_path}"
            )
            raise UnsafeInstallPathError(msg)
        path_bytes = relative_path.as_posix().encode("utf-8")
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        executable = bool(metadata.st_mode & executable_bits)
        _hash_record(digest, b"F", path_bytes)
        digest.update(b"1" if executable else b"0")
        digest.update(metadata.st_size.to_bytes(8, byteorder="big", signed=False))
        with os.fdopen(os.dup(file_fd), "rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)
    finally:
        os.close(file_fd)


def _hash_record(digest: _HashWriter, entry_type: bytes, value: bytes) -> None:
    digest.update(entry_type)
    digest.update(len(value).to_bytes(8, byteorder="big", signed=False))
    digest.update(value)
