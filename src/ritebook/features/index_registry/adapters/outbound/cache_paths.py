"""Canonical registry-owned cache namespace paths."""

from __future__ import annotations

import hashlib
from pathlib import Path

DEFAULT_CACHE_ROOT = "~/.cache/ritebook"
DEFAULT_REGISTRY_PATH = "~/.config/ritebook/indexes.json"


def canonical_registry_path(registry_path: str | None) -> Path:
    """Return the absolute normalized path identifying one registry owner."""
    return Path(registry_path or DEFAULT_REGISTRY_PATH).expanduser().resolve(strict=False)


def registry_cache_root(cache_root: str | None, registry_path: str | None) -> Path:
    """Return the cache namespace owned by one canonical registry path."""
    registry_digest = hashlib.sha256(
        str(canonical_registry_path(registry_path)).encode("utf-8"),
    ).hexdigest()
    return Path(cache_root or DEFAULT_CACHE_ROOT).expanduser() / "registries" / registry_digest
