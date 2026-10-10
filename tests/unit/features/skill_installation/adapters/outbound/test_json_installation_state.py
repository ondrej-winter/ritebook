import hashlib
import json
import stat
from pathlib import Path
from typing import Any, cast

import pytest

from ritebook.features.skill_installation.adapters.outbound import (
    JsonInstallationStateAdapter,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallationStatus,
    InstallationWorkflow,
    OwnedInstallation,
    ReconciliationIssue,
)
from ritebook.features.skill_installation.application.errors import (
    InstallationPersistenceError,
)


def test_json_installation_state_resolves_direct_and_sync_operation_paths(
    tmp_path: Path,
) -> None:
    adapter = JsonInstallationStateAdapter()
    direct_registry = tmp_path / "config" / "installations.json"
    requirements_file = tmp_path / "project" / "config" / "ritebook.toml"
    lockfile = tmp_path / "project" / "custom.lock"

    direct = adapter.direct_paths(str(direct_registry))
    sync = adapter.sync_paths(
        requirements_file=str(requirements_file),
        lockfile_path=str(lockfile),
    )

    assert direct.ownership_path == str(direct_registry)
    assert direct.lock_path == str(direct_registry.parent / "installation.lock")
    assert direct.journal_path == str(
        direct_registry.parent / "installation-transaction.json",
    )
    assert direct.lockfile_path is None
    assert sync.ownership_path == str(
        requirements_file.parent / ".ritebook" / "installations.json",
    )
    assert sync.lock_path == str(requirements_file.parent / ".ritebook" / "install.lock")
    assert sync.journal_path == str(
        requirements_file.parent / ".ritebook" / "transaction.json",
    )
    assert sync.lockfile_path == str(lockfile)


def test_json_installation_state_round_trips_strict_schema_v3_ownership(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".ritebook" / "installations.json"
    adapter = JsonInstallationStateAdapter()
    entries = (
        _owned(target=".agents/skills/zeta", skill_name="zeta"),
        _owned(target=".agents/skills/alpha", skill_name="alpha"),
    )

    state_file = adapter.ownership_file(entries, str(path))
    path.parent.mkdir(parents=True)
    path.write_bytes(state_file.content)
    path.chmod(0o600)

    result = adapter.read_ownership(str(path))
    payload = _read_json(path)

    assert result.entries == tuple(sorted(entries, key=lambda entry: entry.target_id))
    assert result.digest == _bytes_digest(state_file.content)
    assert payload["schema_version"] == 3
    assert payload["installations"][0]["source_branch"] == "refs/heads/main"
    assert [entry["target_id"] for entry in payload["installations"]] == sorted(entry.target_id for entry in entries)
    assert state_file.private is True
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_json_installation_state_reports_ownership_ledger_presence(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".ritebook" / "installations.json"
    adapter = JsonInstallationStateAdapter()

    assert adapter.ownership_exists(str(path)) is False

    path.parent.mkdir(parents=True)
    path.write_text('{"schema_version":3,"installations":[]}\n', encoding="utf-8")

    assert adapter.ownership_exists(str(path)) is True


def test_json_installation_state_reads_missing_state_as_an_absent_snapshot(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.json"

    snapshot = JsonInstallationStateAdapter().read_ownership(str(path))

    assert snapshot.entries == ()
    assert snapshot.digest is None


def test_json_installation_state_reads_exact_raw_state_digest(tmp_path: Path) -> None:
    path = tmp_path / "ritebook.lock"
    content = b'{ "schema_version": 3 }\n'
    path.write_bytes(content)
    adapter = JsonInstallationStateAdapter()

    assert adapter.read_state_digest(str(path)) == _bytes_digest(content)
    assert adapter.read_state_digest(str(tmp_path / "missing.lock")) is None


def test_json_installation_state_bootstraps_sync_ownership_from_schema_v3_lock(
    tmp_path: Path,
) -> None:
    requirements_file = tmp_path / "project" / "ritebook.toml"
    lockfile_path = requirements_file.parent / "ritebook.lock"
    entry = _owned(target=".agents/skills/code-review")
    state_file = JsonInstallationStateAdapter().lockfile(
        (entry,),
        (),
        str(lockfile_path),
        requirements_file="ritebook.toml",
    )
    lockfile_path.parent.mkdir(parents=True)
    lockfile_path.write_bytes(state_file.content)

    result = JsonInstallationStateAdapter().read_lockfile_ownership(
        str(lockfile_path),
        requirements_file=str(requirements_file),
    )

    assert result.entries == (
        OwnedInstallation(
            workflow=InstallationWorkflow.SYNC,
            requirement=entry.requirement,
            index_name=entry.index_name,
            skill_name=entry.skill_name,
            target=entry.target,
            target_id=entry.target_id,
            canonical_target=str(
                (requirements_file.parent / entry.target).resolve(strict=False),
            ),
            source=entry.source,
            source_type=entry.source_type,
            source_revision=entry.source_revision,
            source_branch=entry.source_branch,
            index_digest=entry.index_digest,
            index_schema_version=entry.index_schema_version,
            skill_path=entry.skill_path,
            skill_file=entry.skill_file,
            installed_tree_digest=entry.installed_tree_digest,
            desired=entry.desired,
            status=entry.status,
            target_ref=entry.target_ref,
        ),
    )
    assert result.digest == _bytes_digest(state_file.content)


def test_json_installation_state_hashes_the_exact_bytes_it_parses(
    tmp_path: Path,
) -> None:
    path = tmp_path / "installations.json"
    content = b'{ "schema_version": 3, "installations": [] }\n'
    path.write_bytes(content)

    snapshot = JsonInstallationStateAdapter().read_ownership(str(path))

    assert snapshot.entries == ()
    assert snapshot.digest == _bytes_digest(content)


@pytest.mark.parametrize(
    "entry_override",
    [
        {
            "target": "../outside",
            "target_id": f"sha256:{hashlib.sha256(b'../outside').hexdigest()}",
        },
        {"target_id": f"sha256:{'e' * 64}"},
        {"source": "../local", "source_type": "local_git_repo"},
        {"source_branch": None},
        {"unexpected": True},
    ],
)
def test_json_installation_state_rejects_unsafe_lock_bootstrap_entries(
    tmp_path: Path,
    entry_override: dict[str, object],
) -> None:
    requirements_file = tmp_path / "project" / "ritebook.toml"
    lockfile_path = requirements_file.parent / "ritebook.lock"
    entry = _lock_entry_json(_owned())
    entry.update(entry_override)
    lockfile_path.parent.mkdir(parents=True)
    lockfile_path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "requirements_file": "ritebook.toml",
                "state": "complete",
                "skills": [entry],
                "issues": [],
            },
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        InstallationPersistenceError,
        match=r"ritebook\.lock|target|source",
    ):
        JsonInstallationStateAdapter().read_lockfile_ownership(
            str(lockfile_path),
            requirements_file=str(requirements_file),
        )


@pytest.mark.parametrize(
    "scenario",
    [
        "legacy",
        "schema-v2",
        "unknown-root",
        "unknown-entry",
    ],
)
def test_json_installation_state_rejects_legacy_or_unknown_ownership_fields(
    tmp_path: Path,
    scenario: str,
) -> None:
    path = tmp_path / "installations.json"
    if scenario == "legacy":
        payload: dict[str, object] = {"schema_version": 1, "installations": []}
    elif scenario == "schema-v2":
        payload = {"schema_version": 2, "installations": []}
    elif scenario == "unknown-root":
        payload = {
            "schema_version": 3,
            "installations": [],
            "unexpected": True,
        }
    else:
        payload = {
            "schema_version": 3,
            "installations": [{**_owned_json(), "unexpected": True}],
        }
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        InstallationPersistenceError,
        match=r"schema version 3|malformed",
    ):
        JsonInstallationStateAdapter().read_ownership(str(path))


def test_json_installation_state_rejects_ownership_without_source_branch(
    tmp_path: Path,
) -> None:
    path = tmp_path / "installations.json"
    entry = _owned_json()
    del entry["source_branch"]
    path.write_text(
        json.dumps({"schema_version": 3, "installations": [entry]}),
        encoding="utf-8",
    )

    with pytest.raises(InstallationPersistenceError, match="malformed"):
        JsonInstallationStateAdapter().read_ownership(str(path))


def test_json_installation_state_renders_deterministic_complete_lockfile() -> None:
    entries = (
        _owned(target=".agents/skills/zeta", skill_name="zeta"),
        _owned(target=".agents/skills/alpha", skill_name="alpha"),
    )
    adapter = JsonInstallationStateAdapter()

    first = adapter.lockfile(
        entries,
        (),
        "ritebook.lock",
        requirements_file="ritebook.toml",
    )
    second = adapter.lockfile(
        tuple(reversed(entries)),
        (),
        "ritebook.lock",
        requirements_file="ritebook.toml",
    )
    payload = cast("dict[str, Any]", json.loads(first.content))

    assert first.content == second.content
    assert payload["schema_version"] == 3
    assert payload["state"] == "complete"
    assert payload["issues"] == []
    assert [entry["target_id"] for entry in payload["skills"]] == sorted(entry.target_id for entry in entries)
    assert "canonical_target" not in first.content.decode()
    assert "locked_at" not in first.content.decode()
    assert first.private is False


def test_json_installation_state_renders_truthful_partial_lockfile() -> None:
    retained = _owned(
        target=".agents/skills/old",
        skill_name="old",
        desired=False,
        status=InstallationStatus.LOCAL_CHANGES,
    )
    issue = ReconciliationIssue(
        code="local-changes",
        target=retained.target,
        requirement=retained.requirement,
        detail="target has local changes and was preserved",
    )

    state_file = JsonInstallationStateAdapter().lockfile(
        (retained,),
        (issue,),
        "ritebook.lock",
        requirements_file="ritebook.toml",
    )
    payload = cast("dict[str, Any]", json.loads(state_file.content))

    assert payload["state"] == "partial"
    assert payload["skills"][0]["desired"] is False
    assert payload["skills"][0]["status"] == "local_changes"
    assert payload["issues"] == [
        {
            "code": "local-changes",
            "target": retained.target,
            "requirement": retained.requirement,
            "detail": "target has local changes and was preserved",
        },
    ]


def test_json_installation_state_rejects_local_source_in_shared_lockfile() -> None:
    entry = _owned(source="../local-skills", source_type="local_git_repo")

    with pytest.raises(InstallationPersistenceError, match="portable Git URL"):
        JsonInstallationStateAdapter().lockfile(
            (entry,),
            (),
            "ritebook.lock",
            requirements_file="ritebook.toml",
        )


def _owned(
    *,
    target: str = ".agents/skills/code-review",
    skill_name: str = "code-review",
    source: str = "git@example.com:company/skills.git",
    source_type: str = "git_url",
    desired: bool = True,
    status: InstallationStatus = InstallationStatus.MATERIALIZED,
) -> OwnedInstallation:
    target_id = _digest(target)
    requirement = f"platform-skills/{skill_name}"
    return OwnedInstallation(
        workflow=InstallationWorkflow.SYNC,
        requirement=requirement,
        index_name="platform-skills",
        skill_name=skill_name,
        target=target,
        target_id=target_id,
        canonical_target=str((Path.cwd() / target).resolve(strict=False)),
        source=source,
        source_type=source_type,
        source_revision="a" * 40,
        source_branch="refs/heads/main",
        index_digest=f"sha256:{'b' * 64}",
        index_schema_version=1,
        skill_path=f"skills/{skill_name}",
        skill_file=f"skills/{skill_name}/SKILL.md",
        installed_tree_digest=f"sha256:{'c' * 64}",
        desired=desired,
        status=status,
        target_ref="agents",
    )


def _owned_json() -> dict[str, object]:
    entry = _owned()
    return {
        "workflow": entry.workflow.value,
        "requirement": entry.requirement,
        "index_name": entry.index_name,
        "skill_name": entry.skill_name,
        "target": entry.target,
        "target_id": entry.target_id,
        "canonical_target": entry.canonical_target,
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
        "target_ref": entry.target_ref,
    }


def _lock_entry_json(entry: OwnedInstallation) -> dict[str, object]:
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


def _digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _bytes_digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
