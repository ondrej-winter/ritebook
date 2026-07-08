"""Filesystem adapter for local index registry metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from ritebook.features.index_registry.application.dtos import (
    IndexSourceType,
    RegisteredIndex,
)
from ritebook.features.index_registry.application.errors import (
    IndexRegistryPersistenceError,
)

DEFAULT_REGISTRY_PATH = "~/.config/ritebook/indexes.json"


class FilesystemIndexRegistry:
    """Persist registered index metadata in deterministic JSON."""

    def get(self, name: str, registry_path: str | None) -> RegisteredIndex | None:
        """Return a registered index by name when present."""
        entries = _load_entries(_registry_path(registry_path))
        return entries.get(name)

    def upsert(self, entry: RegisteredIndex, registry_path: str | None) -> None:
        """Insert or replace a registry entry and write the registry file."""
        path = _registry_path(registry_path)
        entries = _load_entries(path)
        entries[entry.name] = entry
        _write_entries(path, entries)


def _registry_path(registry_path: str | None) -> Path:
    return Path(registry_path or DEFAULT_REGISTRY_PATH).expanduser()


def _load_entries(path: Path) -> dict[str, RegisteredIndex]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        msg = f"unable to read index registry: {path}"
        raise IndexRegistryPersistenceError(msg) from err
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        msg = f"unsupported index registry schema: {path}"
        raise IndexRegistryPersistenceError(msg)
    raw_entries = payload.get("indexes", [])
    if not isinstance(raw_entries, list):
        msg = f"index registry indexes must be an array: {path}"
        raise IndexRegistryPersistenceError(msg)
    entries: dict[str, RegisteredIndex] = {}
    try:
        for raw_entry in raw_entries:
            entry = _entry_from_json(cast("dict[str, Any]", raw_entry))
            entries[entry.name] = entry
    except (TypeError, ValueError, KeyError) as err:
        msg = f"index registry contains invalid metadata: {path}"
        raise IndexRegistryPersistenceError(msg) from err
    return entries


def _write_entries(path: Path, entries: dict[str, RegisteredIndex]) -> None:
    payload = {
        "schema_version": 1,
        "indexes": [_entry_to_json(entries[name]) for name in sorted(entries)],
    }
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temp_path.replace(path)
    except OSError as err:
        msg = f"unable to write index registry: {path}"
        raise IndexRegistryPersistenceError(msg) from err


def _entry_from_json(payload: dict[str, Any]) -> RegisteredIndex:
    return RegisteredIndex(
        name=str(payload["name"]),
        published_name=str(payload["published_name"]),
        source=str(payload["source"]),
        source_type=IndexSourceType(str(payload["source_type"])),
        source_cache_path=cast("str | None", payload.get("source_cache_path")),
        cached_index_path=str(payload["cached_index_path"]),
        source_schema_version=int(payload["source_schema_version"]),
        skill_count=int(payload["skill_count"]),
        added_at=str(payload["added_at"]),
        updated_at=str(payload["updated_at"]),
    )


def _entry_to_json(entry: RegisteredIndex) -> dict[str, Any]:
    return {
        "name": entry.name,
        "published_name": entry.published_name,
        "source": entry.source,
        "source_type": entry.source_type.value,
        "source_cache_path": entry.source_cache_path,
        "cached_index_path": entry.cached_index_path,
        "source_schema_version": entry.source_schema_version,
        "skill_count": entry.skill_count,
        "added_at": entry.added_at,
        "updated_at": entry.updated_at,
    }
