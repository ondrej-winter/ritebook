from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from ritebook.features.skill_installation.application.dtos import (
    CommittedSkillHeader,
    GeneratedStateFile,
    InstallableSkill,
    InstallationOperationPaths,
    InstallationStateSnapshot,
    InstallationStatus,
    InstallationWorkflow,
    InstallFromRequirementsCommand,
    InstallSkillCommand,
    OwnedInstallation,
    PlannedInstallTarget,
    ReconciliationIssue,
    RegisteredSkillIndex,
    ResolvedSkillSource,
    SkillRequirement,
    SkillRequirements,
    StagedSkillTree,
    SyncPaths,
    TargetInspection,
)
from ritebook.features.skill_installation.application.errors import (
    CommittedSkillMetadataMismatchError,
    InstallationPersistenceError,
    LocallyModifiedInstallTargetError,
    UnmanagedInstallTargetError,
)
from ritebook.features.skill_installation.application.use_cases import (
    InstallFromRequirements,
    InstallSkill,
)

from .fakes import installable_skill, registered_skill_index


def test_direct_install_establishes_ownership_after_transactional_placement(
    tmp_path: Path,
) -> None:
    target = tmp_path / "skills" / "code-review"
    index = registered_skill_index(name="platform-skills")
    catalog = _Catalog(index=index, skills=(installable_skill(),))
    order: list[str] = []
    installer = _Installer(
        inspections={str(target): _inspection(target, exists=False)},
        order=order,
    )
    validator = _CommittedSkillValidator(order=order)
    state = _StateAdapter(direct_root=tmp_path / "state")
    transactions = _Transactions()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=_SourceResolver(),
        committed_skill_validator=validator,
        installer=installer,
        state=state,
        transactions=transactions,
    )

    result = use_case.execute(
        InstallSkillCommand(
            skill_reference="platform-skills/code-review",
            target=str(target),
        ),
    )

    assert result.ownership_entry.workflow is InstallationWorkflow.DIRECT
    assert result.ownership_entry.canonical_target == str(target.resolve())
    assert result.ownership_entry.installed_tree_digest == _TREE_DIGEST
    assert transactions.transaction.replace_calls == [
        ("/staged/code-review", str(target), None),
    ]
    assert transactions.transaction.committed_files == (state.last_ownership_file,)
    assert state.read_calls == [state.direct_paths(None).ownership_path]
    assert order == ["validate", "plan"]


def test_direct_install_attaches_ownership_snapshot_digest_to_state_candidate(
    tmp_path: Path,
) -> None:
    target = tmp_path / "skills" / "code-review"
    state = _StateAdapter(
        direct_root=tmp_path / "state",
        ownership_digest=_OWNERSHIP_DIGEST,
    )
    transactions = _Transactions()
    use_case = InstallSkill(
        catalog=_Catalog(
            index=registered_skill_index(name="platform-skills"),
            skills=(installable_skill(),),
        ),
        source_resolver=_SourceResolver(),
        committed_skill_validator=_CommittedSkillValidator(),
        installer=_Installer(
            inspections={str(target): _inspection(target, exists=False)},
        ),
        state=state,
        transactions=transactions,
    )

    use_case.execute(
        InstallSkillCommand(
            skill_reference="platform-skills/code-review",
            target=str(target),
        ),
    )

    [candidate] = transactions.transaction.committed_files
    assert candidate.expected_digest == _OWNERSHIP_DIGEST


def test_direct_install_rejects_committed_header_mismatch_before_target_planning(
    tmp_path: Path,
) -> None:
    target = tmp_path / "skills" / "code-review"
    installer = _Installer(
        inspections={str(target): _inspection(target, exists=False)},
    )
    transactions = _Transactions()
    use_case = InstallSkill(
        catalog=_Catalog(
            index=registered_skill_index(name="platform-skills"),
            skills=(installable_skill(description="Indexed description."),),
        ),
        source_resolver=_SourceResolver(),
        committed_skill_validator=_CommittedSkillValidator(
            headers={
                "code-review": CommittedSkillHeader(
                    name="code-review",
                    description="Different committed description.",
                ),
            },
        ),
        installer=installer,
        state=_StateAdapter(direct_root=tmp_path / "state"),
        transactions=transactions,
    )

    with pytest.raises(CommittedSkillMetadataMismatchError, match="does not match"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="platform-skills/code-review",
                target=str(target),
            ),
        )

    assert installer.plan_calls == []
    assert installer.stage_calls == []
    assert transactions.transaction.replace_calls == []
    assert transactions.transaction.committed_files == ()


def test_direct_install_without_force_preserves_unmanaged_existing_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "skills" / "code-review"
    installer = _Installer(
        inspections={str(target): _inspection(target, exists=True, digest=_OLD_DIGEST)},
    )
    use_case = InstallSkill(
        catalog=_Catalog(
            index=registered_skill_index(name="platform-skills"),
            skills=(installable_skill(),),
        ),
        source_resolver=_SourceResolver(),
        committed_skill_validator=_CommittedSkillValidator(),
        installer=installer,
        state=_StateAdapter(direct_root=tmp_path / "state"),
        transactions=_Transactions(),
    )

    with pytest.raises(UnmanagedInstallTargetError, match="not owned"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="platform-skills/code-review",
                target=str(target),
            ),
        )

    assert installer.stage_calls == []


def test_direct_install_force_replaces_unmanaged_existing_target(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "code-review"
    index = registered_skill_index(name="platform-skills")
    installer = _Installer(
        inspections={str(target): _inspection(target, exists=True, digest=_OLD_DIGEST)},
    )
    transactions = _Transactions()
    use_case = InstallSkill(
        catalog=_Catalog(index=index, skills=(installable_skill(),)),
        source_resolver=_SourceResolver(),
        committed_skill_validator=_CommittedSkillValidator(),
        installer=installer,
        state=_StateAdapter(direct_root=tmp_path / "state"),
        transactions=transactions,
    )

    result = use_case.execute(
        InstallSkillCommand(
            skill_reference="platform-skills/code-review",
            target=str(target),
            force=True,
        ),
    )

    assert result.ownership_entry.canonical_target == str(target.resolve())
    assert installer.stage_calls == ["code-review"]
    assert transactions.transaction.replace_calls == [
        ("/staged/code-review", str(target), _OLD_DIGEST),
    ]


def test_direct_install_force_replaces_locally_modified_owned_target(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "code-review"
    installer = _Installer(
        inspections={str(target): _inspection(target, exists=True, digest=_EDITED_DIGEST)},
    )
    state = _StateAdapter(
        direct_root=tmp_path / "state",
        ownership=(_owned(target, digest=_OLD_DIGEST, workflow=InstallationWorkflow.DIRECT),),
    )
    transactions = _Transactions()
    use_case = InstallSkill(
        catalog=_Catalog(
            index=registered_skill_index(name="platform-skills"),
            skills=(installable_skill(),),
        ),
        source_resolver=_SourceResolver(),
        committed_skill_validator=_CommittedSkillValidator(),
        installer=installer,
        state=state,
        transactions=transactions,
    )

    use_case.execute(
        InstallSkillCommand(
            skill_reference="platform-skills/code-review",
            target=str(target),
            force=True,
        ),
    )

    assert transactions.transaction.replace_calls == [
        ("/staged/code-review", str(target), _EDITED_DIGEST),
    ]


def test_direct_install_without_force_preserves_locally_modified_owned_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "skills" / "code-review"
    installer = _Installer(
        inspections={str(target): _inspection(target, exists=True, digest=_EDITED_DIGEST)},
    )
    use_case = InstallSkill(
        catalog=_Catalog(
            index=registered_skill_index(name="platform-skills"),
            skills=(installable_skill(),),
        ),
        source_resolver=_SourceResolver(),
        committed_skill_validator=_CommittedSkillValidator(),
        installer=installer,
        state=_StateAdapter(
            direct_root=tmp_path / "state",
            ownership=(
                _owned(
                    target,
                    digest=_OLD_DIGEST,
                    workflow=InstallationWorkflow.DIRECT,
                ),
            ),
        ),
        transactions=_Transactions(),
    )

    with pytest.raises(LocallyModifiedInstallTargetError, match="local changes"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="platform-skills/code-review",
                target=str(target),
            ),
        )

    assert installer.stage_calls == []


def test_sync_validates_every_selected_header_before_planning_any_target(
    tmp_path: Path,
) -> None:
    index = registered_skill_index(name="platform-skills")
    reader = _RequirementsReader(
        SkillRequirements(
            targets={"agents": ".agents/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="agents"),
                SkillRequirement(name="platform-skills/security-review", target="agents"),
            ),
        ),
    )
    installer = _Installer(inspections={})
    validator = _CommittedSkillValidator(
        headers={
            "code-review": CommittedSkillHeader(
                name="code-review",
                description="Helps with code-review workflows.",
            ),
            "security-review": CommittedSkillHeader(
                name="security-review",
                description="Different committed description.",
            ),
        },
    )
    use_case = _sync_use_case(
        tmp_path,
        reader=reader,
        catalog=_Catalog(
            index=index,
            skills=(
                installable_skill(),
                installable_skill(name="security-review"),
            ),
        ),
        committed_skill_validator=validator,
        installer=installer,
    )

    with pytest.raises(CommittedSkillMetadataMismatchError, match="does not match"):
        use_case.execute(
            InstallFromRequirementsCommand(
                requirements_file=str(tmp_path / "ritebook.toml"),
            ),
        )

    assert [skill.name for _, skill in validator.calls] == [
        "code-review",
        "security-review",
    ]
    assert installer.plan_calls == []
    assert installer.stage_calls == []


def test_sync_refreshes_referenced_aliases_before_catalog_reads(tmp_path: Path) -> None:
    order: list[str] = []
    platform = registered_skill_index(
        name="platform-skills",
        cached_index_path="/cache/indexes/platform-skills/ritebook-index.json",
    )
    company = registered_skill_index(
        name="company-skills",
        cached_index_path="/cache/indexes/company-skills/ritebook-index.json",
    )
    reader = _RequirementsReader(
        SkillRequirements(
            targets={"agents": ".agents/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="agents"),
                SkillRequirement(name="company-skills/security-review", target="agents"),
            ),
        ),
    )
    catalog = _Catalog(
        indexes=(platform, company),
        skills_by_index={
            platform.cached_index_path: (installable_skill(),),
            company.cached_index_path: (installable_skill(name="security-review"),),
        },
        order=order,
    )
    refresher = _Refresher(order=order)
    installer = _Installer(
        inspections={
            str(tmp_path / ".agents/skills/code-review"): _inspection(
                tmp_path / ".agents/skills/code-review",
                exists=False,
            ),
            str(tmp_path / ".agents/skills/security-review"): _inspection(
                tmp_path / ".agents/skills/security-review",
                exists=False,
            ),
        },
    )
    use_case = _sync_use_case(
        tmp_path,
        reader=reader,
        catalog=catalog,
        refresher=refresher,
        installer=installer,
    )

    use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
        ),
    )

    assert refresher.calls == ["company-skills", "platform-skills"]
    first_catalog_read = min(index for index, value in enumerate(order) if value == "get")
    assert all(value == "refresh" for value in order[:first_catalog_read])


def test_sync_commits_successful_target_and_reports_unmanaged_skip(
    tmp_path: Path,
) -> None:
    missing = tmp_path / ".agents/skills/code-review"
    unmanaged = tmp_path / ".agents/skills/security-review"
    index = registered_skill_index(name="platform-skills")
    reader = _RequirementsReader(
        SkillRequirements(
            targets={"agents": ".agents/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="agents"),
                SkillRequirement(name="platform-skills/security-review", target="agents"),
            ),
        ),
    )
    installer = _Installer(
        inspections={
            str(missing): _inspection(missing, exists=False),
            str(unmanaged): _inspection(unmanaged, exists=True, digest=_OLD_DIGEST),
        },
    )
    state = _StateAdapter(sync_root=tmp_path / ".ritebook")
    transactions = _Transactions()
    use_case = _sync_use_case(
        tmp_path,
        reader=reader,
        catalog=_Catalog(
            index=index,
            skills=(
                installable_skill(),
                installable_skill(name="security-review"),
            ),
        ),
        installer=installer,
        state=state,
        transactions=transactions,
    )

    result = use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
        ),
    )

    assert result.installed_count == 1
    assert result.updated_count == 0
    assert result.unchanged_count == 0
    assert [issue.code for issue in result.issues] == ["unmanaged-target"]
    assert transactions.transaction.replace_calls == [
        ("/staged/code-review", str(missing), None),
    ]
    assert len(state.last_ownership_entries) == 1
    assert state.last_lock_issues == result.issues
    assert transactions.transaction.committed_files == (state.last_lockfile,)


def test_sync_force_replaces_unmanaged_and_locally_modified_declared_targets(
    tmp_path: Path,
) -> None:
    unmanaged = tmp_path / ".agents/skills/code-review"
    edited = tmp_path / ".agents/skills/security-review"
    ownership = (_owned(edited, skill_name="security-review", digest=_OLD_DIGEST),)
    index = registered_skill_index(name="platform-skills")
    state = _StateAdapter(sync_root=tmp_path / ".ritebook", lock_ownership=ownership)
    transactions = _Transactions()
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(
            SkillRequirements(
                targets={"agents": ".agents/skills"},
                skills=(
                    SkillRequirement(name="platform-skills/code-review", target="agents"),
                    SkillRequirement(name="platform-skills/security-review", target="agents"),
                ),
            ),
        ),
        catalog=_Catalog(
            index=index,
            skills=(
                installable_skill(),
                installable_skill(name="security-review"),
            ),
        ),
        installer=_Installer(
            inspections={
                str(unmanaged): _inspection(unmanaged, exists=True, digest=_OLD_DIGEST),
                str(edited): _inspection(edited, exists=True, digest=_EDITED_DIGEST),
            },
        ),
        state=state,
        transactions=transactions,
    )

    result = use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
            force=True,
        ),
    )

    assert result.updated_count == 2
    assert result.issues == ()
    assert transactions.transaction.replace_calls == [
        ("/staged/code-review", str(unmanaged), _OLD_DIGEST),
        ("/staged/security-review", str(edited), _EDITED_DIGEST),
    ]
    assert all(entry.status is InstallationStatus.MATERIALIZED for entry in state.last_ownership_entries)


def test_sync_renders_only_selected_lockfile_snapshot(
    tmp_path: Path,
) -> None:
    state = _StateAdapter(
        sync_root=tmp_path / ".ritebook",
        ownership_digest=_OWNERSHIP_DIGEST,
        lockfile_digest=_LOCKFILE_DIGEST,
    )
    transactions = _Transactions()
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(SkillRequirements(targets={}, skills=())),
        state=state,
        transactions=transactions,
    )

    use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
        ),
    )

    [lockfile] = transactions.transaction.committed_files
    assert lockfile.expected_digest is None
    assert state.read_calls == []


def test_sync_leaves_undeclared_previously_owned_targets_untouched(
    tmp_path: Path,
) -> None:
    prior_target = tmp_path / ".agents/skills/prior"
    state = _StateAdapter(
        sync_root=tmp_path / ".ritebook",
        ownership=(_owned(prior_target, skill_name="prior", digest=_OLD_DIGEST),),
    )
    transactions = _Transactions()
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(SkillRequirements(targets={}, skills=())),
        installer=_Installer(inspections={}),
        state=state,
        transactions=transactions,
    )

    result = use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
        ),
    )

    assert result.issues == ()
    assert transactions.transaction.replace_calls == []
    assert state.last_ownership_entries == ()


def test_sync_no_change_performs_no_target_mutation(tmp_path: Path) -> None:
    target = tmp_path / ".agents/skills/code-review"
    existing = _owned(target, digest=_TREE_DIGEST)
    index = registered_skill_index(name="platform-skills")
    state = _StateAdapter(sync_root=tmp_path / ".ritebook", lock_ownership=(existing,))
    transactions = _Transactions()
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(
            SkillRequirements(
                targets={"agents": ".agents/skills"},
                skills=(SkillRequirement(name="platform-skills/code-review", target="agents"),),
            ),
        ),
        catalog=_Catalog(index=index, skills=(installable_skill(),)),
        installer=_Installer(
            inspections={str(target): _inspection(target, exists=True, digest=_TREE_DIGEST)},
        ),
        state=state,
        transactions=transactions,
    )

    result = use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
        ),
    )

    assert result.unchanged_count == 1
    assert result.issues == ()
    assert transactions.transaction.replace_calls == []


def test_sync_never_opens_a_recovery_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse_transaction(*, lock_path: str, journal_path: str) -> None:
        del lock_path, journal_path
        msg = "sync opened the recovery transaction"
        raise AssertionError(msg)

    transactions = _Transactions()
    monkeypatch.setattr(transactions, "open", refuse_transaction)
    result = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(SkillRequirements(targets={}, skills=())),
        transactions=transactions,
    ).execute(InstallFromRequirementsCommand(requirements_file=str(tmp_path / "ritebook.toml")))

    assert result.issues == ()


@pytest.mark.parametrize("lock_failure", [False, True])
def test_sync_attempts_all_staging_cleanup_and_retains_primary_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    lock_failure: bool,
) -> None:
    names = ("code-review", "security-review")
    installer = _Installer(
        inspections={
            str(tmp_path / "skills" / name): _inspection(tmp_path / "skills" / name, exists=False) for name in names
        }
    )
    cleaned: list[str] = []

    def fail_cleanup(staged: StagedSkillTree) -> None:
        cleaned.append(staged.cleanup_path)
        msg = f"staging retained at {staged.cleanup_path}"
        raise InstallationPersistenceError(msg)

    def fail_lock(_candidate: GeneratedStateFile) -> None:
        msg = "primary lockfile write failure"
        raise InstallationPersistenceError(msg)

    transactions = _Transactions()
    if lock_failure:
        monkeypatch.setattr(transactions.transaction, "write_lockfile", fail_lock)
    monkeypatch.setattr(installer, "cleanup_staged", fail_cleanup)
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(
            SkillRequirements(
                targets={"agents": "skills"},
                skills=tuple(SkillRequirement(name=f"platform-skills/{name}", target="agents") for name in names),
            )
        ),
        catalog=_Catalog(
            index=registered_skill_index(name="platform-skills"),
            skills=tuple(installable_skill(name=name) for name in names),
        ),
        installer=installer,
        transactions=transactions,
    )
    with pytest.raises(InstallationPersistenceError) as error:
        use_case.execute(InstallFromRequirementsCommand(requirements_file=str(tmp_path / "ritebook.toml")))
    assert cleaned == [f"/staged/{name}-root" for name in names]
    assert all(path in str(error.value) for path in cleaned)
    if lock_failure:
        assert "primary lockfile write failure" in str(error.value)
        assert transactions.transaction.committed_files == ()
    assert len(transactions.transaction.replace_calls) == 2


@pytest.mark.parametrize("modified", [False, True])
def test_sync_uses_selected_lock_despite_conflicting_ledger(
    tmp_path: Path,
    *,
    modified: bool,
) -> None:
    target = tmp_path / ".agents/skills/code-review"
    locked = _owned(target, digest=_TREE_DIGEST)
    index = registered_skill_index(name="platform-skills")
    state = _StateAdapter(
        sync_root=tmp_path / ".ritebook",
        ownership=(_owned(target, digest=_OLD_DIGEST),),
        lock_ownership=(locked,),
        lockfile_digest=_LOCKFILE_DIGEST,
    )
    transactions = _Transactions()
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(
            SkillRequirements(
                targets={"agents": ".agents/skills"},
                skills=(
                    SkillRequirement(
                        name="platform-skills/code-review",
                        target="agents",
                    ),
                ),
            ),
        ),
        catalog=_Catalog(index=index, skills=(installable_skill(),)),
        installer=_Installer(
            inspections={
                str(target): _inspection(target, exists=True, digest=_EDITED_DIGEST if modified else _TREE_DIGEST),
            },
        ),
        state=state,
        transactions=transactions,
    )

    result = use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
            lockfile_path=str(tmp_path / "custom.lock"),
        ),
    )

    assert result.unchanged_count == int(not modified)
    assert [issue.code for issue in result.issues] == (["local-changes"] if modified else [])
    assert result.ownership_entries[0].installed_tree_digest == _TREE_DIGEST
    assert transactions.transaction.replace_calls == []
    [lockfile] = transactions.transaction.committed_files
    assert lockfile.expected_digest is None
    assert lockfile.path == str(tmp_path / "custom.lock")
    assert state.read_calls == []
    assert state.last_ownership_entries[0].canonical_target == str(target)


@pytest.mark.parametrize("force", [False, True])
def test_sync_rejects_invalid_lock_despite_existing_ledger(
    tmp_path: Path,
    *,
    force: bool,
) -> None:
    state = _InvalidLockState(sync_root=tmp_path / ".ritebook")
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(SkillRequirements(targets={}, skills=())),
        state=state,
    )

    with pytest.raises(InstallationPersistenceError):
        use_case.execute(
            InstallFromRequirementsCommand(
                requirements_file=str(tmp_path / "ritebook.toml"),
                lockfile_path=str(tmp_path / "custom.lock"),
                force=force,
            )
        )

    assert state.read_calls == []


@pytest.mark.parametrize("force", [False, True])
def test_sync_missing_lock_never_adopts_matching_content_from_ledger(
    tmp_path: Path,
    *,
    force: bool,
) -> None:
    target = tmp_path / ".agents/skills/code-review"
    state = _StateAdapter(
        sync_root=tmp_path / ".ritebook",
        ownership=(_owned(target, digest=_TREE_DIGEST),),
    )
    transactions = _Transactions()
    result = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(
            SkillRequirements(
                targets={"agents": ".agents/skills"},
                skills=(SkillRequirement(name="platform-skills/code-review", target="agents"),),
            )
        ),
        catalog=_Catalog(index=registered_skill_index(name="platform-skills"), skills=(installable_skill(),)),
        installer=_Installer(inspections={str(target): _inspection(target, exists=True, digest=_TREE_DIGEST)}),
        state=state,
        transactions=transactions,
    ).execute(InstallFromRequirementsCommand(requirements_file=str(tmp_path / "ritebook.toml"), force=force))

    assert result.unchanged_count == 0
    assert result.updated_count == int(force)
    assert [issue.code for issue in result.issues] == ([] if force else ["unmanaged-target"])
    assert state.read_calls == []


def test_sync_does_not_bootstrap_ownership_from_legacy_undesired_lock_entry(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".agents/skills/code-review"
    legacy_undesired = _owned(target, digest=_TREE_DIGEST, desired=False)
    state = _StateAdapter(
        sync_root=tmp_path / ".ritebook",
        lock_ownership=(legacy_undesired,),
        lockfile_digest=_LOCKFILE_DIGEST,
    )
    transactions = _Transactions()
    use_case = _sync_use_case(
        tmp_path,
        reader=_RequirementsReader(
            SkillRequirements(
                targets={"agents": ".agents/skills"},
                skills=(
                    SkillRequirement(
                        name="platform-skills/code-review",
                        target="agents",
                    ),
                ),
            ),
        ),
        catalog=_Catalog(
            index=registered_skill_index(name="platform-skills"),
            skills=(installable_skill(),),
        ),
        installer=_Installer(
            inspections={
                str(target): _inspection(target, exists=True, digest=_TREE_DIGEST),
            },
        ),
        state=state,
        transactions=transactions,
    )

    result = use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file=str(tmp_path / "ritebook.toml"),
        ),
    )

    assert [issue.code for issue in result.issues] == ["unmanaged-target"]
    assert transactions.transaction.replace_calls == []
    assert state.last_ownership_entries == ()


_TREE_DIGEST = f"sha256:{'1' * 64}"
_OLD_DIGEST = f"sha256:{'2' * 64}"
_EDITED_DIGEST = f"sha256:{'3' * 64}"
_OWNERSHIP_DIGEST = f"sha256:{'4' * 64}"
_LOCKFILE_DIGEST = f"sha256:{'5' * 64}"


class _RequirementsReader:
    def __init__(self, requirements: SkillRequirements) -> None:
        self.requirements = requirements

    def read_requirements(self, _requirements_file: str) -> SkillRequirements:
        return self.requirements


class _Refresher:
    def __init__(self, *, order: list[str] | None = None) -> None:
        self.calls: list[str] = []
        self.order = order

    def refresh(self, name: str, registry_path: str | None) -> None:
        del registry_path
        self.calls.append(name)
        if self.order is not None:
            self.order.append("refresh")


class _Catalog:
    def __init__(
        self,
        *,
        index: RegisteredSkillIndex | None = None,
        indexes: tuple[RegisteredSkillIndex, ...] = (),
        skills: tuple[InstallableSkill, ...] = (),
        skills_by_index: dict[str, tuple[InstallableSkill, ...]] | None = None,
        order: list[str] | None = None,
    ) -> None:
        all_indexes = indexes or ((index,) if index is not None else ())
        self.indexes = {entry.name: entry for entry in all_indexes}
        self.skills = skills
        self.skills_by_index = skills_by_index or {}
        self.order = order

    def get_index(
        self,
        name: str,
        registry_path: str | None,
    ) -> RegisteredSkillIndex | None:
        del registry_path
        if self.order is not None:
            self.order.append("get")
        return self.indexes.get(name)

    def read_skills(
        self,
        cached_index_path: str,
        index_digest: str,
    ) -> tuple[InstallableSkill, ...]:
        del index_digest
        if self.order is not None:
            self.order.append("read")
        return self.skills_by_index.get(cached_index_path, self.skills)


class _SourceResolver:
    @contextmanager
    def open_source(
        self,
        _index: RegisteredSkillIndex,
    ) -> Iterator[ResolvedSkillSource]:
        yield ResolvedSkillSource(
            source="git@example.com:company/skills.git",
            source_type="git_url",
            repository_path="/snapshot",
            source_revision="a" * 40,
            source_branch="refs/heads/main",
            index_digest=f"sha256:{'b' * 64}",
        )


class _CommittedSkillValidator:
    def __init__(
        self,
        *,
        headers: dict[str, CommittedSkillHeader] | None = None,
        order: list[str] | None = None,
    ) -> None:
        self.headers = headers or {}
        self.order = order
        self.calls: list[tuple[ResolvedSkillSource, InstallableSkill]] = []

    def validate(
        self,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
    ) -> CommittedSkillHeader:
        self.calls.append((source, skill))
        if self.order is not None:
            self.order.append("validate")
        return self.headers.get(
            skill.name,
            CommittedSkillHeader(
                name=skill.name,
                description=skill.description,
            ),
        )


class _Installer:
    def __init__(
        self,
        *,
        inspections: dict[str, TargetInspection],
        order: list[str] | None = None,
    ) -> None:
        self.inspections = inspections
        self.order = order
        self.plan_calls: list[str] = []
        self.stage_calls: list[str] = []

    def plan_target(self, target: str) -> PlannedInstallTarget:
        self.plan_calls.append(target)
        if self.order is not None:
            self.order.append("plan")
        return PlannedInstallTarget(
            requested_target=target,
            canonical_target=str(Path(target).resolve(strict=False)),
        )

    def inspect_target(self, target: PlannedInstallTarget) -> TargetInspection:
        return self.inspections[target.canonical_target]

    def stage(
        self,
        *,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
        target: PlannedInstallTarget,
    ) -> StagedSkillTree:
        del source, target
        self.stage_calls.append(skill.name)
        return StagedSkillTree(
            staged_path=f"/staged/{skill.name}",
            cleanup_path=f"/staged/{skill.name}-root",
            installed_tree_digest=_TREE_DIGEST,
        )

    def cleanup_staged(self, _staged: StagedSkillTree) -> None:
        return None


class _StateAdapter:
    def __init__(
        self,
        *,
        direct_root: Path | None = None,
        sync_root: Path | None = None,
        ownership: tuple[OwnedInstallation, ...] = (),
        lock_ownership: tuple[OwnedInstallation, ...] = (),
        ownership_digest: str | None = None,
        lockfile_digest: str | None = None,
    ) -> None:
        self.direct_root = direct_root
        self.sync_root = sync_root
        self.ownership = ownership
        self.lock_ownership = lock_ownership
        self.ownership_digest = ownership_digest
        self.lockfile_digest = lockfile_digest
        self.read_calls: list[str] = []
        self.last_ownership_entries: tuple[OwnedInstallation, ...] = ()
        self.last_lock_issues: tuple[ReconciliationIssue, ...] = ()
        self.last_ownership_file = GeneratedStateFile(
            path="/state/installations.json",
            content=b"ownership",
            private=True,
        )
        self.last_lockfile = GeneratedStateFile(
            path="/state/ritebook.lock",
            content=b"lock",
            private=False,
        )

    def direct_paths(self, _registry_path: str | None) -> InstallationOperationPaths:
        assert self.direct_root is not None
        return InstallationOperationPaths(
            lock_path=str(self.direct_root / "install.lock"),
            journal_path=str(self.direct_root / "transaction.json"),
            ownership_path=str(self.direct_root / "installations.json"),
        )

    def sync_paths(
        self,
        *,
        requirements_file: str,
        lockfile_path: str | None,
    ) -> SyncPaths:
        del requirements_file
        assert self.sync_root is not None
        return SyncPaths(
            lockfile_path=lockfile_path or str(self.sync_root.parent / "ritebook.lock"),
        )

    def read_ownership(self, ownership_path: str) -> InstallationStateSnapshot:
        self.read_calls.append(ownership_path)
        return InstallationStateSnapshot(self.ownership, self.ownership_digest)

    def read_lockfile_ownership(
        self,
        _lockfile_path: str,
        *,
        requirements_file: str,
    ) -> InstallationStateSnapshot:
        del requirements_file
        ownership = tuple(entry for entry in self.lock_ownership if entry.desired)
        return InstallationStateSnapshot(ownership, self.lockfile_digest)

    def ownership_file(
        self,
        entries: tuple[OwnedInstallation, ...],
        ownership_path: str,
        *,
        expected_digest: str | None,
    ) -> GeneratedStateFile:
        self.last_ownership_entries = entries
        self.last_ownership_file = GeneratedStateFile(
            path=ownership_path,
            content=b"ownership",
            private=True,
            expected_digest=expected_digest,
        )
        return self.last_ownership_file

    def lockfile(
        self,
        entries: tuple[OwnedInstallation, ...],
        issues: tuple[ReconciliationIssue, ...],
        lockfile_path: str,
        *,
        requirements_file: str,
    ) -> GeneratedStateFile:
        del requirements_file
        self.last_ownership_entries = entries
        self.last_lock_issues = issues
        self.last_lockfile = GeneratedStateFile(
            path=lockfile_path,
            content=b"lock",
            private=False,
        )
        return self.last_lockfile


class _InvalidLockState(_StateAdapter):
    def read_lockfile_ownership(
        self,
        _lockfile_path: str,
        *,
        requirements_file: str,
    ) -> InstallationStateSnapshot:
        del requirements_file
        msg = "Invalid lockfile"
        raise InstallationPersistenceError(msg)


class _Transaction:
    def __init__(self) -> None:
        self.replace_calls: list[tuple[str, str, str | None]] = []
        self.committed_files: tuple[GeneratedStateFile, ...] = ()

    def replace_tree(
        self,
        *,
        staged_path: str,
        target_path: str,
        expected_digest: str | None,
    ) -> None:
        self.replace_calls.append((staged_path, target_path, expected_digest))

    def write_lockfile(self, candidate: GeneratedStateFile) -> None:
        self.committed_files = (candidate,)

    def commit_state(self, files: tuple[GeneratedStateFile, ...]) -> None:
        self.committed_files = files


class _Transactions:
    def __init__(self) -> None:
        self.transaction = _Transaction()

    @contextmanager
    def open(self, *, lock_path: str, journal_path: str) -> Iterator[_Transaction]:
        del lock_path, journal_path
        yield self.transaction


def _sync_use_case(
    tmp_path: Path,
    *,
    reader: _RequirementsReader,
    catalog: _Catalog | None = None,
    committed_skill_validator: _CommittedSkillValidator | None = None,
    refresher: _Refresher | None = None,
    installer: _Installer | None = None,
    state: _StateAdapter | None = None,
    transactions: _Transactions | None = None,
) -> InstallFromRequirements:
    return InstallFromRequirements(
        requirements_reader=reader,
        index_refresher=refresher or _Refresher(),
        catalog=catalog or _Catalog(),
        source_resolver=_SourceResolver(),
        committed_skill_validator=(committed_skill_validator or _CommittedSkillValidator()),
        installer=installer or _Installer(inspections={}),
        state=state or _StateAdapter(sync_root=tmp_path / ".ritebook"),
        writer=(transactions or _Transactions()).transaction,
    )


def _inspection(
    target: Path,
    *,
    exists: bool,
    digest: str | None = None,
) -> TargetInspection:
    return TargetInspection(
        canonical_target=str(target.resolve(strict=False)),
        exists=exists,
        installed_tree_digest=digest,
    )


def _owned(
    target: Path,
    *,
    skill_name: str = "code-review",
    digest: str,
    desired: bool = True,
    workflow: InstallationWorkflow = InstallationWorkflow.SYNC,
) -> OwnedInstallation:
    return OwnedInstallation(
        workflow=workflow,
        requirement=f"platform-skills/{skill_name}",
        index_name="platform-skills",
        skill_name=skill_name,
        target=f".agents/skills/{skill_name}",
        target_id=_target_id(f".agents/skills/{skill_name}"),
        canonical_target=str(target.resolve(strict=False)),
        source="git@example.com:company/skills.git",
        source_type="git_url",
        source_revision="a" * 40,
        source_branch="refs/heads/main",
        index_digest=f"sha256:{'b' * 64}",
        index_schema_version=1,
        skill_path=f"skills/{skill_name}",
        skill_file=f"skills/{skill_name}/SKILL.md",
        installed_tree_digest=digest,
        desired=desired,
        target_ref="agents",
    )


def edited_target_entry(entry: OwnedInstallation) -> dict[str, object]:
    return {field: getattr(entry, field) for field in entry.__dataclass_fields__ if field not in {"desired", "status"}}


def _target_id(value: str) -> str:
    import hashlib  # noqa: PLC0415

    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"
