"""Filesystem adapter for cached index contents."""

from __future__ import annotations

import hashlib
import os
import tempfile
from contextlib import suppress
from pathlib import Path

from ritebook.features.index_registry.application.errors import IndexCacheError

DEFAULT_CACHE_ROOT = "~/.cache/ritebook"
SHA256_HEX_LENGTH = 64


class FilesystemIndexCache:
    """Write cached ritebook-index.json contents under the local index alias."""

    def cached_index_path(
        self,
        *,
        name: str,
        index_digest: str,
        cache_root: str | None,
    ) -> str:
        """Return a content-addressed cache path for a local index alias."""
        digest = _digest_hex(index_digest)
        return str(
            _cache_root(cache_root) / "indexes" / name / digest / "ritebook-index.json",
        )

    def write_index(
        self,
        *,
        name: str,
        content: str,
        index_digest: str,
        cache_root: str | None,
        preserve_path: str | None,
    ) -> str:
        """Write and synchronize one immutable cache generation."""
        _require_matching_digest(content, index_digest)
        path = Path(
            self.cached_index_path(
                name=name,
                index_digest=index_digest,
                cache_root=cache_root,
            ),
        )
        alias_root = path.parent.parent
        _recover_alias_root(
            alias_root,
            preserve_path=preserve_path,
            candidate_path=str(path),
        )
        if path.exists():
            if path.read_text(encoding="utf-8") != content:
                msg = f"cached index generation does not match digest for {name}"
                raise IndexCacheError(msg)
            return str(path)
        temp_path: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
            )
            temp_path = Path(temp_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temp_path.replace(path)
        except OSError as err:
            msg = f"unable to write cached index for {name}"
            raise IndexCacheError(msg) from err
        finally:
            if temp_path is not None:
                with suppress(OSError):
                    temp_path.unlink(missing_ok=True)
            if not path.exists():
                with suppress(OSError):
                    path.parent.rmdir()
        return str(path)

    def discard_index(
        self,
        *,
        name: str,
        cached_index_path: str,
        cache_root: str | None,
    ) -> None:
        """Remove a content-addressed generation owned by this cache root."""
        alias_root = _cache_root(cache_root) / "indexes" / name
        path = Path(cached_index_path)
        if not _is_owned_generation(path, alias_root):
            return
        try:
            path.unlink(missing_ok=True)
            path.parent.rmdir()
        except OSError as err:
            msg = f"unable to discard cached index generation for {name}"
            raise IndexCacheError(msg) from err


def _cache_root(cache_root: str | None) -> Path:
    return Path(cache_root or DEFAULT_CACHE_ROOT).expanduser()


def _digest_hex(index_digest: str) -> str:
    prefix = "sha256:"
    digest = index_digest.removeprefix(prefix)
    if not index_digest.startswith(prefix) or len(digest) != SHA256_HEX_LENGTH:
        msg = "Index digest must use sha256 with 64 lowercase hexadecimal characters."
        raise IndexCacheError(msg)
    try:
        int(digest, 16)
    except ValueError as err:
        msg = "Index digest must use sha256 with 64 lowercase hexadecimal characters."
        raise IndexCacheError(msg) from err
    if digest != digest.lower():
        msg = "Index digest must use lowercase hexadecimal characters."
        raise IndexCacheError(msg)
    return digest


def _require_matching_digest(content: str, index_digest: str) -> None:
    actual = hashlib.sha256(content.encode()).hexdigest()
    if actual != _digest_hex(index_digest):
        msg = "Cached index content does not match its validated digest."
        raise IndexCacheError(msg)


def _recover_alias_root(
    alias_root: Path,
    *,
    preserve_path: str | None,
    candidate_path: str,
) -> None:
    if not alias_root.exists():
        return
    preserved = {candidate_path}
    if preserve_path is not None:
        preserved.add(preserve_path)
    try:
        for child in alias_root.iterdir():
            if child.is_dir():
                index_path = child / "ritebook-index.json"
                for temporary_path in child.glob(".ritebook-index.json.*.tmp"):
                    temporary_path.unlink(missing_ok=True)
                if str(index_path) not in preserved and _is_digest_directory(child):
                    with suppress(FileNotFoundError):
                        index_path.unlink()
                    with suppress(OSError):
                        child.rmdir()
                continue
            if child.name.startswith(".ritebook-index.json.") and child.name.endswith(
                ".tmp",
            ):
                child.unlink(missing_ok=True)
    except OSError as err:
        msg = f"unable to recover index cache for {alias_root.name}"
        raise IndexCacheError(msg) from err


def _is_owned_generation(path: Path, alias_root: Path) -> bool:
    return (
        path.name == "ritebook-index.json"
        and path.parent.parent == alias_root
        and _is_digest_directory(path.parent)
    )


def _is_digest_directory(path: Path) -> bool:
    return len(path.name) == SHA256_HEX_LENGTH and all(
        character in "0123456789abcdef" for character in path.name
    )
