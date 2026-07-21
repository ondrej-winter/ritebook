"""Persist requirements-install lockfiles as deterministic JSON."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ritebook.features.skill_installation.application.errors import (
    InstallationPersistenceError,
)

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallationManifestEntry,
        LockfileManifestEntry,
    )

SCHEMA_VERSION = 1
DEFAULT_LOCKFILE_PATH = Path("ritebook.lock")


class JsonLockfileAdapter:
    """JSON-backed full-rewrite writer for repo-local lockfiles."""

    def write_installation(
        self,
        entry: InstallationManifestEntry,
        registry_path: str | None,
        *,
        force: bool,
    ) -> None:
        """Reject direct installation writes; this adapter owns lockfiles."""
        msg = "JsonLockfileAdapter does not write installations"
        raise NotImplementedError(msg)

    def write_lockfile(
        self,
        entries: tuple[LockfileManifestEntry, ...],
        lockfile_path: str | None,
        *,
        requirements_file: str,
    ) -> None:
        """Persist a complete deterministic lockfile for installed requirements."""
        path = _lockfile_path(lockfile_path)
        sorted_entries = sorted(
            entries,
            key=lambda item: (item.index_name, item.skill_name),
        )
        _atomic_write_json(
            path,
            {
                "schema_version": SCHEMA_VERSION,
                "requirements_file": requirements_file,
                "skills": [_entry_to_json(entry) for entry in sorted_entries],
            },
        )


def _lockfile_path(lockfile_path: str | None) -> Path:
    if lockfile_path is None:
        return DEFAULT_LOCKFILE_PATH
    return Path(lockfile_path).expanduser()


def _entry_to_json(entry: LockfileManifestEntry) -> dict[str, Any]:
    data: dict[str, Any] = {
        "requirement": entry.requirement,
        "index_name": entry.index_name,
        "skill_name": entry.skill_name,
        "target": entry.target,
        "source": entry.source,
        "source_type": entry.source_type,
        "source_revision": entry.source_revision,
        "index_digest": entry.index_digest,
        "index_schema_version": entry.index_schema_version,
        "skill_path": entry.skill_path,
        "skill_file": entry.skill_file,
        "locked_at": entry.locked_at,
    }
    if entry.target_ref is not None:
        data["target_ref"] = entry.target_ref
    return data


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    try:
        parent = path.parent
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=parent,
            delete=False,
        ) as temp_file:
            json.dump(data, temp_file, indent=2)
            temp_file.write("\n")
            temp_name = temp_file.name
        Path(temp_name).replace(path)
    except OSError as err:
        msg = f"lockfile cannot be written: {path}"
        raise InstallationPersistenceError(msg) from err
