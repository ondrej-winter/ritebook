"""Filesystem adapter for cached index contents."""

from __future__ import annotations

from pathlib import Path

from ritebook.features.index_registry.application.errors import IndexCacheError

DEFAULT_CACHE_ROOT = "~/.cache/ritebook"


class FilesystemIndexCache:
    """Write cached ritebook-index.json contents under the effective index name."""

    def cached_index_path(self, *, name: str, cache_root: str | None) -> str:
        """Return the cache path for an effective index name."""
        return str(
            _cache_root(cache_root) / "indexes" / name / "ritebook-index.json",
        )

    def write_index(self, *, name: str, content: str, cache_root: str | None) -> str:
        """Write cached index contents via temp file replacement."""
        path = Path(self.cached_index_path(name=name, cache_root=cache_root))
        temp_path = path.with_name(f".{path.name}.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(path)
        except OSError as err:
            msg = f"unable to write cached index for {name}"
            raise IndexCacheError(msg) from err
        return str(path)


def _cache_root(cache_root: str | None) -> Path:
    return Path(cache_root or DEFAULT_CACHE_ROOT).expanduser()
