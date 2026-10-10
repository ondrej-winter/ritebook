"""Read strict ownership state and render deterministic schema-v3 state files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, cast

from ritebook.features.skill_installation.application.dtos import (
    GeneratedStateFile,
    InstallationOperationPaths,
    InstallationStateSnapshot,
    InstallationStatus,
    InstallationWorkflow,
    OwnedInstallation,
)
from ritebook.features.skill_installation.application.errors import (
    InstallationPersistenceError,
)
from ritebook.shared_kernel import require_safe_persisted_source

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ritebook.features.skill_installation.application.dtos import (
        ReconciliationIssue,
    )

SCHEMA_VERSION = 3
DEFAULT_DIRECT_STATE_PATH = Path.home() / ".config" / "ritebook" / "installations.json"
OWNERSHIP_ROOT_FIELDS = frozenset({"schema_version", "installations"})
OWNERSHIP_ENTRY_FIELDS = frozenset(
    {
        "workflow",
        "requirement",
        "index_name",
        "skill_name",
        "target",
        "target_id",
        "canonical_target",
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
OPTIONAL_OWNERSHIP_ENTRY_FIELDS = frozenset({"target_ref"})
LOCK_ROOT_FIELDS = frozenset(
    {"schema_version", "requirements_file", "state", "skills", "issues"},
)
LOCK_ENTRY_FIELDS = frozenset(
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
OPTIONAL_LOCK_ENTRY_FIELDS = frozenset({"target_ref"})
LOCK_ISSUE_FIELDS = frozenset({"code", "target", "detail"})
OPTIONAL_LOCK_ISSUE_FIELDS = frozenset({"requirement"})


class JsonInstallationStateAdapter:
    """Strict generated-state reader and deterministic candidate renderer."""

    def direct_paths(self, registry_path: str | None) -> InstallationOperationPaths:
        """Resolve direct-install ownership, lock, and journal paths."""
        ownership = _resolved_path(registry_path, default=DEFAULT_DIRECT_STATE_PATH)
        return InstallationOperationPaths(
            lock_path=str(ownership.parent / "installation.lock"),
            journal_path=str(ownership.parent / "installation-transaction.json"),
            ownership_path=str(ownership),
        )

    def sync_paths(
        self,
        *,
        requirements_file: str,
        lockfile_path: str | None,
    ) -> InstallationOperationPaths:
        """Resolve repository-local ownership, lock, journal, and lockfile paths."""
        requirements = Path(requirements_file).expanduser().resolve(strict=False)
        state_root = requirements.parent / ".ritebook"
        lockfile = _resolved_path(
            lockfile_path,
            default=requirements.parent / "ritebook.lock",
        )
        return InstallationOperationPaths(
            lock_path=str(state_root / "install.lock"),
            journal_path=str(state_root / "transaction.json"),
            ownership_path=str(state_root / "installations.json"),
            lockfile_path=str(lockfile),
        )

    def read_ownership(self, ownership_path: str) -> InstallationStateSnapshot:
        """Read and strictly validate schema-v3 ownership state."""
        path = Path(ownership_path)
        if not path.exists():
            return InstallationStateSnapshot(entries=(), digest=None)
        payload, digest = _read_json_object(path)
        if payload.get("schema_version") != SCHEMA_VERSION:
            msg = (
                "installation ownership state requires schema version 3; inspect "
                "and remove or relocate legacy targets before reinstalling"
            )
            raise InstallationPersistenceError(msg)
        if set(payload) != OWNERSHIP_ROOT_FIELDS:
            msg = f"installation ownership state is malformed: {path}"
            raise InstallationPersistenceError(msg)
        installations = payload.get("installations")
        if not isinstance(installations, list):
            msg = f"installation ownership state is malformed: {path}"
            raise InstallationPersistenceError(msg)
        entries = tuple(
            _owned_from_json(entry, position=position, path=path)
            for position, entry in enumerate(installations)
        )
        if len({entry.target_id for entry in entries}) != len(entries):
            msg = f"installation ownership state contains duplicate targets: {path}"
            raise InstallationPersistenceError(msg)
        return InstallationStateSnapshot(
            entries=tuple(sorted(entries, key=lambda entry: entry.target_id)),
            digest=digest,
        )

    def ownership_exists(self, ownership_path: str) -> bool:
        """Return whether a local ownership ledger exists."""
        return Path(ownership_path).exists()

    def read_lockfile_ownership(
        self,
        lockfile_path: str,
        *,
        requirements_file: str,
    ) -> InstallationStateSnapshot:
        """Read strict portable schema-v3 lock state as local sync ownership."""
        path = Path(lockfile_path)
        if not path.exists():
            return InstallationStateSnapshot(entries=(), digest=None)
        payload, digest = _read_json_object(path)
        if payload.get("schema_version") != SCHEMA_VERSION:
            msg = (
                "ritebook.lock requires schema version 3 before it can bootstrap "
                "local installation ownership"
            )
            raise InstallationPersistenceError(msg)
        if set(payload) != LOCK_ROOT_FIELDS:
            msg = f"ritebook.lock schema-v3 root is malformed: {path}"
            raise InstallationPersistenceError(msg)
        if payload.get("state") not in {"complete", "partial"}:
            msg = f"ritebook.lock schema-v3 root is malformed: {path}"
            raise InstallationPersistenceError(msg)
        if (
            not isinstance(payload.get("requirements_file"), str)
            or not payload["requirements_file"]
        ):
            msg = f"ritebook.lock schema-v3 root is malformed: {path}"
            raise InstallationPersistenceError(msg)
        _validate_lock_issues(payload.get("issues"), path=path)
        skills = payload.get("skills")
        if not isinstance(skills, list):
            msg = f"ritebook.lock schema-v3 root is malformed: {path}"
            raise InstallationPersistenceError(msg)
        root = Path(requirements_file).expanduser().resolve(strict=False).parent
        entries = tuple(
            _lock_owned_from_json(entry, position=position, path=path, root=root)
            for position, entry in enumerate(skills)
        )
        if len({entry.target_id for entry in entries}) != len(entries):
            msg = f"ritebook.lock contains duplicate target identities: {path}"
            raise InstallationPersistenceError(msg)
        return InstallationStateSnapshot(
            entries=tuple(sorted(entries, key=lambda entry: entry.target_id)),
            digest=digest,
        )

    def read_state_digest(self, path: str) -> str | None:
        """Return the exact current file-byte digest without parsing its contents."""
        state_path = Path(path)
        if not state_path.exists():
            return None
        try:
            content = state_path.read_bytes()
        except OSError as err:
            msg = f"generated installation state cannot be read: {state_path}"
            raise InstallationPersistenceError(msg) from err
        return _bytes_digest(content)

    def ownership_file(
        self,
        entries: tuple[OwnedInstallation, ...],
        ownership_path: str,
        *,
        expected_digest: str | None = None,
    ) -> GeneratedStateFile:
        """Render deterministic private schema-v3 ownership state."""
        document: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "installations": [
                _ownership_entry_to_json(entry)
                for entry in sorted(entries, key=lambda item: item.target_id)
            ],
        }
        return GeneratedStateFile(
            path=str(Path(ownership_path).expanduser()),
            content=_json_bytes(document),
            private=True,
            expected_digest=expected_digest,
        )

    def lockfile(
        self,
        entries: tuple[OwnedInstallation, ...],
        issues: tuple[ReconciliationIssue, ...],
        lockfile_path: str,
        *,
        requirements_file: str,
        expected_digest: str | None = None,
    ) -> GeneratedStateFile:
        """Render portable deterministic schema-v3 mixed reconciliation state."""
        for entry in entries:
            if entry.source_type == "local_git_repo":
                msg = (
                    "ritebook.lock requires a portable Git URL source; register the "
                    "index from a Git URL and rerun skills sync"
                )
                raise InstallationPersistenceError(msg)
            _require_safe_source(entry.source, entry.source_type)
        sorted_issues = sorted(
            issues,
            key=lambda issue: (issue.target, issue.code, issue.requirement or ""),
        )
        complete = not sorted_issues and all(
            entry.desired and entry.status is InstallationStatus.MATERIALIZED
            for entry in entries
        )
        document: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "requirements_file": requirements_file,
            "state": "complete" if complete else "partial",
            "skills": [
                _lock_entry_to_json(entry)
                for entry in sorted(entries, key=lambda item: item.target_id)
            ],
            "issues": [_issue_to_json(issue) for issue in sorted_issues],
        }
        return GeneratedStateFile(
            path=str(Path(lockfile_path).expanduser()),
            content=_json_bytes(document),
            private=False,
            expected_digest=expected_digest,
        )


def _resolved_path(value: str | None, *, default: Path) -> Path:
    path = default if value is None else Path(value).expanduser()
    return path.resolve(strict=False)


def _read_json_object(path: Path) -> tuple[dict[str, object], str]:
    try:
        content = path.read_bytes()
        payload = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        msg = f"installation ownership state cannot be read: {path}"
        raise InstallationPersistenceError(msg) from err
    if not isinstance(payload, dict):
        msg = f"installation ownership state is malformed: {path}"
        raise InstallationPersistenceError(msg)
    return cast("dict[str, object]", payload), _bytes_digest(content)


def _owned_from_json(
    value: object,
    *,
    position: int,
    path: Path,
) -> OwnedInstallation:
    if not isinstance(value, dict):
        msg = f"installation ownership state is malformed: {path}"
        raise InstallationPersistenceError(msg)
    entry = cast("Mapping[object, object]", value)
    fields = set(entry)
    required = OWNERSHIP_ENTRY_FIELDS
    if not required.issubset(fields) or not fields.issubset(
        required | OPTIONAL_OWNERSHIP_ENTRY_FIELDS,
    ):
        msg = f"installation ownership state is malformed: {path}"
        raise InstallationPersistenceError(msg)
    try:
        source = _required_str(entry, "source")
        source_type = _required_str(entry, "source_type")
        _require_safe_source(source, source_type)
        return OwnedInstallation(
            workflow=InstallationWorkflow(_required_str(entry, "workflow")),
            requirement=_required_str(entry, "requirement"),
            index_name=_required_str(entry, "index_name"),
            skill_name=_required_str(entry, "skill_name"),
            target=_required_str(entry, "target"),
            target_id=_required_str(entry, "target_id"),
            canonical_target=_required_str(entry, "canonical_target"),
            source=source,
            source_type=source_type,
            source_revision=_required_str(entry, "source_revision"),
            source_branch=_required_str(entry, "source_branch"),
            index_digest=_required_str(entry, "index_digest"),
            index_schema_version=_required_int(entry, "index_schema_version"),
            skill_path=_required_str(entry, "skill_path"),
            skill_file=_required_str(entry, "skill_file"),
            installed_tree_digest=_required_str(entry, "installed_tree_digest"),
            desired=_required_bool(entry, "desired"),
            status=InstallationStatus(_required_str(entry, "status")),
            target_ref=_optional_str(entry, "target_ref"),
        )
    except (TypeError, ValueError) as err:
        msg = f"invalid ownership entry at position {position}: {err}"
        raise InstallationPersistenceError(msg) from err


def _lock_owned_from_json(
    value: object,
    *,
    position: int,
    path: Path,
    root: Path,
) -> OwnedInstallation:
    if not isinstance(value, dict):
        msg = f"ritebook.lock skill entry at position {position} is malformed: {path}"
        raise InstallationPersistenceError(msg)
    entry = cast("Mapping[object, object]", value)
    fields = set(entry)
    if not LOCK_ENTRY_FIELDS.issubset(fields) or not fields.issubset(
        LOCK_ENTRY_FIELDS | OPTIONAL_LOCK_ENTRY_FIELDS,
    ):
        msg = f"ritebook.lock skill entry at position {position} is malformed: {path}"
        raise InstallationPersistenceError(msg)
    try:
        target = _required_str(entry, "target")
        normalized_target = _safe_portable_target(target)
        target_id = _required_str(entry, "target_id")
        _require_matching_target_id(target_id, normalized_target)
        source = _required_str(entry, "source")
        source_type = _required_str(entry, "source_type")
        _require_portable_lock_source(source_type)
        _require_safe_source(source, source_type)
        return OwnedInstallation(
            workflow=InstallationWorkflow.SYNC,
            requirement=_required_str(entry, "requirement"),
            index_name=_required_str(entry, "index_name"),
            skill_name=_required_str(entry, "skill_name"),
            target=normalized_target,
            target_id=target_id,
            canonical_target=str(root / Path(*PurePosixPath(normalized_target).parts)),
            source=source,
            source_type=source_type,
            source_revision=_required_str(entry, "source_revision"),
            source_branch=_required_str(entry, "source_branch"),
            index_digest=_required_str(entry, "index_digest"),
            index_schema_version=_required_int(entry, "index_schema_version"),
            skill_path=_required_str(entry, "skill_path"),
            skill_file=_required_str(entry, "skill_file"),
            installed_tree_digest=_required_str(
                entry,
                "installed_tree_digest",
            ),
            desired=_required_bool(entry, "desired"),
            status=InstallationStatus(_required_str(entry, "status")),
            target_ref=_optional_str(entry, "target_ref"),
        )
    except (InstallationPersistenceError, TypeError, ValueError) as err:
        msg = f"invalid ritebook.lock skill entry at position {position}: {err}"
        raise InstallationPersistenceError(msg) from err


def _validate_lock_issues(value: object, *, path: Path) -> None:
    if not isinstance(value, list):
        msg = f"ritebook.lock schema-v3 root is malformed: {path}"
        raise InstallationPersistenceError(msg)
    for issue in value:
        if not isinstance(issue, dict):
            msg = f"ritebook.lock issue entry is malformed: {path}"
            raise InstallationPersistenceError(msg)
        fields = set(issue)
        if not LOCK_ISSUE_FIELDS.issubset(fields) or not fields.issubset(
            LOCK_ISSUE_FIELDS | OPTIONAL_LOCK_ISSUE_FIELDS,
        ):
            msg = f"ritebook.lock issue entry is malformed: {path}"
            raise InstallationPersistenceError(msg)
        for field_name in LOCK_ISSUE_FIELDS:
            field_value = issue.get(field_name)
            if not isinstance(field_value, str) or not field_value:
                msg = f"ritebook.lock issue entry is malformed: {path}"
                raise InstallationPersistenceError(msg)
        requirement = issue.get("requirement")
        if requirement is not None and (
            not isinstance(requirement, str) or not requirement
        ):
            msg = f"ritebook.lock issue entry is malformed: {path}"
            raise InstallationPersistenceError(msg)


def _safe_portable_target(value: str) -> str:
    if "\\" in value:
        msg = "lockfile target must be a safe portable relative POSIX path"
        raise ValueError(msg)
    target = PurePosixPath(value)
    if target.is_absolute() or not value or ".." in target.parts:
        msg = "lockfile target must be a safe portable relative POSIX path"
        raise ValueError(msg)
    normalized = target.as_posix()
    if normalized in {"", "."}:
        msg = "lockfile target must be a safe portable relative POSIX path"
        raise ValueError(msg)
    return normalized


def _target_id(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _require_matching_target_id(target_id: str, target: str) -> None:
    if target_id != _target_id(target):
        msg = "lockfile target_id does not match its portable target"
        raise ValueError(msg)


def _require_portable_lock_source(source_type: str) -> None:
    if source_type == "local_git_repo":
        msg = "ritebook.lock ownership bootstrap requires a portable Git URL source"
        raise ValueError(msg)


def _ownership_entry_to_json(entry: OwnedInstallation) -> dict[str, object]:
    _require_safe_source(entry.source, entry.source_type)
    data = _common_entry_to_json(entry)
    data.update(
        {
            "workflow": entry.workflow.value,
            "canonical_target": entry.canonical_target,
        },
    )
    return data


def _lock_entry_to_json(entry: OwnedInstallation) -> dict[str, object]:
    return _common_entry_to_json(entry)


def _common_entry_to_json(entry: OwnedInstallation) -> dict[str, object]:
    data: dict[str, object] = {
        "requirement": entry.requirement,
        "index_name": entry.index_name,
        "skill_name": entry.skill_name,
        "target": entry.target,
        "target_id": entry.target_id,
        "source": entry.source,
        "source_type": entry.source_type,
        "source_revision": entry.source_revision,
        "source_branch": entry.source_branch,
        "index_digest": entry.index_digest,
        "index_schema_version": entry.index_schema_version,
        "skill_path": entry.skill_path,
        "skill_file": entry.skill_file,
        "installed_tree_digest": entry.installed_tree_digest,
        "desired": entry.desired,
        "status": entry.status.value,
    }
    if entry.target_ref is not None:
        data["target_ref"] = entry.target_ref
    return data


def _issue_to_json(issue: ReconciliationIssue) -> dict[str, object]:
    data: dict[str, object] = {
        "code": issue.code,
        "target": issue.target,
        "detail": issue.detail,
    }
    if issue.requirement is not None:
        data["requirement"] = issue.requirement
    return data


def _required_str(entry: Mapping[object, object], field_name: str) -> str:
    value = entry.get(field_name)
    if not isinstance(value, str) or not value:
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    return value


def _optional_str(entry: Mapping[object, object], field_name: str) -> str | None:
    value = entry.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        msg = f"{field_name} must be a non-empty string when present"
        raise ValueError(msg)
    return value


def _required_int(entry: Mapping[object, object], field_name: str) -> int:
    value = entry.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"{field_name} must be an integer"
        raise TypeError(msg)
    return value


def _required_bool(entry: Mapping[object, object], field_name: str) -> bool:
    value = entry.get(field_name)
    if not isinstance(value, bool):
        msg = f"{field_name} must be a boolean"
        raise TypeError(msg)
    return value


def _require_safe_source(source: str, source_type: str) -> None:
    try:
        require_safe_persisted_source(source, source_type)
    except ValueError as err:
        msg = "installation state contains an unsafe Git source; reinstall it"
        raise InstallationPersistenceError(msg) from err


def _json_bytes(document: dict[str, object]) -> bytes:
    return f"{json.dumps(document, indent=2)}\n".encode()


def _bytes_digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"
