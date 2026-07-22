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
    ContributionLockfileEntryNotFoundError,
    ContributionLockfileReadError,
)
from ritebook.features.skill_contribution.application.ports import (
    ContributionLockfilePort,
)
from ritebook.shared_kernel import require_safe_persisted_source

if TYPE_CHECKING:
    from collections.abc import Mapping

SCHEMA_VERSION = 1
DEFAULT_LOCKFILE_PATH = Path("ritebook.lock")
LOCAL_GIT_REPO_SOURCE_TYPE = "local_git_repo"


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
        source = _required_str(typed_entry, "source", position=position)
        source_type = _required_str(typed_entry, "source_type", position=position)
        if source_type == LOCAL_GIT_REPO_SOURCE_TYPE:
            msg = (
                "local repository sources are not supported in shared ritebook.lock; "
                "register the index from a Git URL and reinstall to regenerate "
                "ritebook.lock"
            )
            raise ContributionLockfileReadError(msg)
        require_safe_persisted_source(source, source_type)
        return ContributionLockfileEntry(
            requirement=_required_str(typed_entry, "requirement", position=position),
            index_name=_required_str(typed_entry, "index_name", position=position),
            skill_name=_required_str(typed_entry, "skill_name", position=position),
            target=_required_str(typed_entry, "target", position=position),
            source=source,
            source_type=source_type,
            source_revision=_required_str(
                typed_entry,
                "source_revision",
                position=position,
            ),
            index_digest=_required_str(
                typed_entry,
                "index_digest",
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
        if field_name in {"source_revision", "index_digest"}:
            msg = (
                f"lockfile skill entry at position {position} is missing verified "
                f"{field_name}; regenerate ritebook.lock by running ritebook install"
            )
            raise ContributionLockfileReadError(msg)
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
