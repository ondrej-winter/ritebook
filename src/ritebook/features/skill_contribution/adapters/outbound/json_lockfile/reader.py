"""Read repo-local lockfiles for skill contribution publishing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionSkillReference,
)
from ritebook.features.skill_contribution.application.errors import (
    AmbiguousContributionSkillReferenceError,
    ContributionLockfileEntryNotFoundError,
    ContributionLockfileReadError,
)
from ritebook.features.skill_contribution.application.ports import (
    ContributionLockfilePort,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

SCHEMA_VERSION = 1
DEFAULT_LOCKFILE_PATH = Path("ritebook.lock")


class JsonContributionLockfileReader(ContributionLockfilePort):
    """Read and resolve publishable entries from a JSON `ritebook.lock`."""

    def resolve_entry(
        self,
        reference: ContributionSkillReference,
        lockfile_path: str | None,
    ) -> ContributionLockfileEntry:
        """Resolve exactly one publishable lockfile entry for a reference."""
        entries = _read_entries(_resolved_lockfile_path(lockfile_path))
        candidates = tuple(
            entry for entry in entries if entry.index_name == reference.index_name
        )

        for entry in candidates:
            if entry.requirement == reference.requirement:
                return entry

        for entry in candidates:
            if entry.skill_path == reference.skill_selector:
                return entry

        matching_names = tuple(
            entry for entry in candidates if entry.skill_name == reference.skill_name
        )
        if len(matching_names) == 1:
            return matching_names[0]
        if len(matching_names) > 1:
            msg = (
                f"skill reference {reference.requirement} is ambiguous; "
                "use an exact skill path from ritebook.lock"
            )
            raise AmbiguousContributionSkillReferenceError(msg)

        msg = f"no lockfile entry found for {reference.requirement}"
        raise ContributionLockfileEntryNotFoundError(msg)


def _resolved_lockfile_path(lockfile_path: str | None) -> Path:
    if lockfile_path is None:
        return DEFAULT_LOCKFILE_PATH
    return Path(lockfile_path).expanduser()


def _read_entries(path: Path) -> tuple[ContributionLockfileEntry, ...]:
    payload = _read_payload(path)
    schema_version = payload.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        msg = f"unsupported lockfile schema_version: {schema_version}"
        raise ContributionLockfileReadError(msg)

    skills = payload.get("skills")
    if not isinstance(skills, list):
        msg = "ritebook.lock must contain a skills array"
        raise ContributionLockfileReadError(msg)

    return tuple(
        _entry_from_json(entry, position=position)
        for position, entry in enumerate(skills)
    )


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as err:
        msg = f"lockfile cannot be read: {path}"
        raise ContributionLockfileReadError(msg) from err

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as err:
        msg = f"lockfile is not valid JSON: {path}"
        raise ContributionLockfileReadError(msg) from err

    if not isinstance(payload, dict):
        msg = "ritebook.lock must contain a JSON object"
        raise ContributionLockfileReadError(msg)
    return payload


def _entry_from_json(
    entry: object,
    *,
    position: int,
) -> ContributionLockfileEntry:
    if not isinstance(entry, dict):
        msg = "ritebook.lock skills entries must be JSON objects"
        raise ContributionLockfileReadError(msg)
    typed_entry = cast("Mapping[object, object]", entry)

    try:
        return ContributionLockfileEntry(
            requirement=_required_str(typed_entry, "requirement", position=position),
            index_name=_required_str(typed_entry, "index_name", position=position),
            skill_name=_required_str(typed_entry, "skill_name", position=position),
            target=_required_str(typed_entry, "target", position=position),
            source=_required_str(typed_entry, "source", position=position),
            source_type=_required_str(typed_entry, "source_type", position=position),
            source_revision=_required_str(
                typed_entry,
                "source_revision",
                position=position,
            ),
            skill_path=_required_str(typed_entry, "skill_path", position=position),
            skill_file=_required_str(typed_entry, "skill_file", position=position),
            index_schema_version=_required_int(
                typed_entry,
                "index_schema_version",
                position=position,
            ),
        )
    except ValueError as err:
        msg = f"invalid lockfile skill entry at position {position}: {err}"
        raise ContributionLockfileReadError(msg) from err


def _required_str(
    entry: Mapping[object, object],
    field_name: str,
    *,
    position: int,
) -> str:
    value = entry.get(field_name)
    if not isinstance(value, str) or not value:
        msg = f"lockfile skill entry at position {position} must include {field_name}"
        raise ContributionLockfileReadError(msg)
    return value


def _required_int(
    entry: Mapping[object, object],
    field_name: str,
    *,
    position: int,
) -> int:
    value = entry.get(field_name)
    if not isinstance(value, int):
        msg = f"lockfile skill entry at position {position} must include {field_name}"
        raise ContributionLockfileReadError(msg)
    return value
