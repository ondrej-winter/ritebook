"""Persist direct skill installation state as deterministic JSON."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ritebook.features.skill_installation.application.errors import (
    ConflictingRecordedTargetError,
    InstallationPersistenceError,
)

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallationManifestEntry,
        LockfileManifestEntry,
    )

SCHEMA_VERSION = 1
DEFAULT_REGISTRY_PATH = Path.home() / ".config" / "ritebook" / "installations.json"


class JsonInstallationRegistryAdapter:
    """JSON-backed writer for generated direct-install registry state."""

    def write_installation(
        self,
        entry: InstallationManifestEntry,
        registry_path: str | None,
        *,
        force: bool,
    ) -> None:
        """Persist one installation entry with target conflict protection."""
        path = _registry_path(registry_path)
        target = _stored_target(entry.target)
        entries = _read_entries(path)
        updated_entries = _upsert_entry(
            entries,
            _entry_to_json(entry, target),
            force=force,
        )
        _atomic_write_json(
            path,
            {
                "schema_version": SCHEMA_VERSION,
                "installations": sorted(
                    updated_entries,
                    key=lambda item: item["target"],
                ),
            },
        )

    def write_lockfile(
        self,
        entries: tuple[LockfileManifestEntry, ...],
        lockfile_path: str | None,
        *,
        requirements_file: str,
    ) -> None:
        """Reject lockfile writes; this adapter owns direct installation state."""
        msg = "JsonInstallationRegistryAdapter does not write lockfiles"
        raise NotImplementedError(msg)


def _registry_path(registry_path: str | None) -> Path:
    if registry_path is None:
        return DEFAULT_REGISTRY_PATH
    return Path(registry_path).expanduser()


def _stored_target(target: str) -> str:
    return str(Path(target).expanduser().resolve(strict=False))


def _read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as err:
        msg = f"installation registry cannot be read: {path}"
        raise InstallationPersistenceError(msg) from err

    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        msg = f"installation registry has unsupported schema: {path}"
        raise InstallationPersistenceError(msg)
    entries = data.get("installations")
    if not isinstance(entries, list) or not all(
        isinstance(item, dict) for item in entries
    ):
        msg = f"installation registry is malformed: {path}"
        raise InstallationPersistenceError(msg)
    typed_entries = cast("list[dict[str, Any]]", entries)
    for entry in typed_entries:
        if not _has_required_provenance(entry):
            msg = (
                "installation registry contains legacy entries without verified "
                f"provenance: {path}; remove it and reinstall the recorded skills"
            )
            raise InstallationPersistenceError(msg)
    return typed_entries


def _has_required_provenance(entry: dict[str, Any]) -> bool:
    return all(
        isinstance(entry.get(field_name), str) and bool(entry[field_name])
        for field_name in ("source_revision", "index_digest")
    )


def _upsert_entry(
    entries: list[dict[str, Any]],
    new_entry: dict[str, Any],
    *,
    force: bool,
) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    replaced = False
    for existing in entries:
        if existing.get("target") != new_entry["target"]:
            updated.append(existing)
            continue

        if existing.get("requirement") != new_entry["requirement"] and not force:
            msg = (
                f"target {new_entry['target']} is already recorded for "
                f"{existing.get('requirement')}; use --force to replace it"
            )
            raise ConflictingRecordedTargetError(msg)
        if not replaced:
            updated.append(new_entry)
            replaced = True

    if not replaced:
        updated.append(new_entry)
    return updated


def _entry_to_json(entry: InstallationManifestEntry, target: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "requirement": entry.requirement,
        "index_name": entry.index_name,
        "skill_name": entry.skill_name,
        "target": target,
        "source": entry.source,
        "source_type": entry.source_type,
        "source_revision": entry.source_revision,
        "index_digest": entry.index_digest,
        "index_schema_version": entry.index_schema_version,
        "skill_path": entry.skill_path,
        "skill_file": entry.skill_file,
        "installed_at": entry.installed_at,
    }
    return data


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as temp_file:
            json.dump(data, temp_file, indent=2)
            temp_file.write("\n")
            temp_name = temp_file.name
        Path(temp_name).replace(path)
    except OSError as err:
        msg = f"installation registry cannot be written: {path}"
        raise InstallationPersistenceError(msg) from err
