"""Read strict schema-v3 repo-local lockfiles for skill contribution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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

SCHEMA_VERSION = 3
DEFAULT_LOCKFILE_PATH = Path("ritebook.lock")
LOCAL_GIT_REPO_SOURCE_TYPE = "local_git_repo"
PUBLISHABLE_STATUSES = frozenset({"materialized", "local_changes"})
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
ROOT_FIELDS = frozenset(
    {"schema_version", "requirements_file", "state", "skills", "issues"},
)
ENTRY_FIELDS = frozenset(
    {
        "requirement",
        "index_name",
        "skill_name",
        "target",
        "target_id",
        "source",
        "source_type",
        "source_revision",
        "source_branch",
        "index_digest",
        "index_schema_version",
        "skill_path",
        "skill_file",
        "installed_tree_digest",
        "desired",
        "status",
    },
)
OPTIONAL_ENTRY_FIELDS = frozenset({"target_ref"})
ISSUE_FIELDS = frozenset({"code", "target", "detail"})
OPTIONAL_ISSUE_FIELDS = frozenset({"requirement"})


@dataclass(frozen=True)
class _ParsedEntry:
    entry: ContributionLockfileEntry
    desired: bool
    status: str


class JsonContributionLockfileReader(ContributionLockfilePort):
    """Read and resolve publishable entries from a schema-v3 `ritebook.lock`."""

    def resolve_entry(
        self,
        reference: ContributionSkillReference,
        lockfile_path: str | None,
    ) -> ContributionLockfileEntry:
        """Resolve one exact publishable lockfile entry for a reference."""
        entries = _read_entries(_resolved_lockfile_path(lockfile_path))
        for parsed in entries:
            if (
                parsed.entry.requirement == reference.requirement
                and parsed.desired
                and parsed.status in PUBLISHABLE_STATUSES
            ):
                return parsed.entry

        msg = f"no lockfile entry found for {reference.requirement}"
        raise ContributionLockfileEntryNotFoundError(msg)


def _resolved_lockfile_path(lockfile_path: str | None) -> Path:
    if lockfile_path is None:
        return DEFAULT_LOCKFILE_PATH
    return Path(lockfile_path).expanduser()


def _read_entries(path: Path) -> tuple[_ParsedEntry, ...]:
    payload = _read_payload(path)
    schema_version = payload.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        msg = f"unsupported lockfile schema_version: {schema_version}"
        raise ContributionLockfileReadError(msg)
    if set(payload) != ROOT_FIELDS:
        msg = "ritebook.lock schema-v3 root is malformed"
        raise ContributionLockfileReadError(msg)
    if not isinstance(payload.get("requirements_file"), str) or not payload["requirements_file"]:
        msg = "ritebook.lock must contain a non-empty requirements_file"
        raise ContributionLockfileReadError(msg)
    if payload.get("state") not in {"complete", "partial"}:
        msg = "ritebook.lock schema-v3 root is malformed"
        raise ContributionLockfileReadError(msg)
    _validate_issues(payload.get("issues"))

    skills = payload.get("skills")
    if not isinstance(skills, list):
        msg = "ritebook.lock must contain a skills array"
        raise ContributionLockfileReadError(msg)
    return tuple(_entry_from_json(entry, position=position) for position, entry in enumerate(skills))


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
    return cast("dict[str, Any]", payload)


def _validate_issues(value: object) -> None:
    if not isinstance(value, list):
        msg = "ritebook.lock schema-v2 root is malformed"
        raise ContributionLockfileReadError(msg)
    for issue in value:
        if not isinstance(issue, dict):
            msg = "ritebook.lock issues entries must be JSON objects"
            raise ContributionLockfileReadError(msg)
        fields = set(issue)
        if not ISSUE_FIELDS.issubset(fields) or not fields.issubset(
            ISSUE_FIELDS | OPTIONAL_ISSUE_FIELDS,
        ):
            msg = "ritebook.lock issue entry is malformed"
            raise ContributionLockfileReadError(msg)
        for field_name in ISSUE_FIELDS:
            field_value = issue.get(field_name)
            if not isinstance(field_value, str) or not field_value:
                msg = "ritebook.lock issue entry is malformed"
                raise ContributionLockfileReadError(msg)
        requirement = issue.get("requirement")
        if requirement is not None and (not isinstance(requirement, str) or not requirement):
            msg = "ritebook.lock issue entry is malformed"
            raise ContributionLockfileReadError(msg)


def _entry_from_json(entry: object, *, position: int) -> _ParsedEntry:
    if not isinstance(entry, dict):
        msg = "ritebook.lock skills entries must be JSON objects"
        raise ContributionLockfileReadError(msg)
    typed_entry = cast("Mapping[object, object]", entry)
    fields = set(typed_entry)
    missing_fields = sorted(ENTRY_FIELDS - fields)
    if missing_fields:
        field_name = missing_fields[0]
        if field_name in {
            "source_revision",
            "source_branch",
            "index_digest",
            "installed_tree_digest",
        }:
            msg = (
                f"lockfile skill entry at position {position} is missing verified "
                f"{field_name}; regenerate ritebook.lock by running "
                "ritebook skills sync"
            )
        else:
            msg = f"lockfile skill entry at position {position} must include {field_name}"
        raise ContributionLockfileReadError(msg)
    if not fields.issubset(ENTRY_FIELDS | OPTIONAL_ENTRY_FIELDS):
        msg = f"lockfile skill entry at position {position} is malformed"
        raise ContributionLockfileReadError(msg)

    try:
        source = _required_str(typed_entry, "source", position=position)
        source_type = _required_str(typed_entry, "source_type", position=position)
        if source_type == LOCAL_GIT_REPO_SOURCE_TYPE:
            msg = (
                "local repository sources are not supported in shared ritebook.lock; "
                "register the index from a Git URL and regenerate ritebook.lock"
            )
            raise ContributionLockfileReadError(msg)
        require_safe_persisted_source(source, source_type)
        target_id = _required_str(typed_entry, "target_id", position=position)
        installed_tree_digest = _required_str(
            typed_entry,
            "installed_tree_digest",
            position=position,
        )
        _require_digest(target_id, field_name="target_id")
        _require_digest(
            installed_tree_digest,
            field_name="installed_tree_digest",
        )
        desired = _required_bool(typed_entry, "desired", position=position)
        status = _required_str(typed_entry, "status", position=position)
        if status not in {"materialized", "local_changes", "retained"}:
            msg = f"invalid lockfile skill entry at position {position}: invalid status"
            raise ContributionLockfileReadError(msg)
        return _ParsedEntry(
            entry=ContributionLockfileEntry(
                requirement=_required_str(
                    typed_entry,
                    "requirement",
                    position=position,
                ),
                index_name=_required_str(
                    typed_entry,
                    "index_name",
                    position=position,
                ),
                skill_name=_required_str(
                    typed_entry,
                    "skill_name",
                    position=position,
                ),
                target=_required_str(typed_entry, "target", position=position),
                source=source,
                source_type=source_type,
                source_revision=_required_str(
                    typed_entry,
                    "source_revision",
                    position=position,
                ),
                source_branch=_required_str(
                    typed_entry,
                    "source_branch",
                    position=position,
                ),
                index_digest=_required_str(
                    typed_entry,
                    "index_digest",
                    position=position,
                ),
                skill_path=_required_str(
                    typed_entry,
                    "skill_path",
                    position=position,
                ),
                skill_file=_required_str(
                    typed_entry,
                    "skill_file",
                    position=position,
                ),
                index_schema_version=_required_int(
                    typed_entry,
                    "index_schema_version",
                    position=position,
                ),
                installed_tree_digest=installed_tree_digest,
            ),
            desired=desired,
            status=status,
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
        if field_name in {
            "source_revision",
            "source_branch",
            "index_digest",
            "installed_tree_digest",
        }:
            msg = (
                f"lockfile skill entry at position {position} is missing verified "
                f"{field_name}; regenerate ritebook.lock by running "
                "ritebook skills sync"
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
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"lockfile skill entry at position {position} must include {field_name}"
        raise ContributionLockfileReadError(msg)
    return value


def _required_bool(
    entry: Mapping[object, object],
    field_name: str,
    *,
    position: int,
) -> bool:
    value = entry.get(field_name)
    if not isinstance(value, bool):
        msg = f"lockfile skill entry at position {position} must include {field_name}"
        raise ContributionLockfileReadError(msg)
    return value


def _require_digest(value: str, *, field_name: str) -> None:
    if not DIGEST_PATTERN.fullmatch(value):
        msg = f"{field_name} must use sha256:<64 lowercase hex>"
        raise ValueError(msg)
