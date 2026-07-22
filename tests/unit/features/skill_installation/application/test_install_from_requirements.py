from datetime import UTC, datetime
from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound.json_lockfile import (
    JsonLockfileAdapter,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    InstallFromRequirementsCommand,
    ResolvedSkillSource,
    SkillRequirement,
    SkillRequirements,
)
from ritebook.features.skill_installation.application.errors import (
    DuplicateInstallTargetError,
    DuplicateSkillRequirementError,
    ExistingInstallTargetError,
    GeneratedStateCommitError,
    InstallationPersistenceError,
    InstalledTargetCleanupError,
    PartialInstallationError,
    SkillSourceResolutionError,
    UndefinedInstallTargetError,
    UnknownInstallIndexError,
    UnknownInstallSkillError,
)
from ritebook.features.skill_installation.application.use_cases import (
    InstallFromRequirements,
)

from .fakes import (
    FakeInstallationManifest,
    FakeRequirementsReader,
    FakeSkillCatalog,
    FakeSkillInstaller,
    FakeSkillSourceResolver,
    installable_skill,
    registered_skill_index,
)


def test_install_from_requirements_resolves_target_nickname_and_writes_lockfile() -> (
    None
):
    index = registered_skill_index(name="platform-skills")
    skill = installable_skill(name="code-review")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (skill,)},
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = _use_case(
        reader=reader,
        catalog=catalog,
        installer=installer,
        manifest=manifest,
    )

    result = use_case.execute(
        InstallFromRequirementsCommand(
            requirements_file="ritebook.toml",
            registry_path="/tmp/indexes.json",
            lockfile_path="/tmp/ritebook.lock",
        ),
    )

    assert result.installed_count == 1
    assert reader.read_calls == ["ritebook.toml"]
    assert catalog.get_index_calls == [("platform-skills", "/tmp/indexes.json")]
    assert installer.install_calls == [
        (FakeSkillSourceResolver().source, skill, ".claude/skills/code-review", False),
    ]
    assert manifest.lockfile_write_calls == [
        (result.lockfile_entries, "/tmp/ritebook.lock", "ritebook.toml"),
    ]
    entry = result.lockfile_entries[0]
    assert entry.requirement == "platform-skills/code-review"
    assert entry.target == ".claude/skills/code-review"
    assert entry.target_ref == "claude"
    assert entry.locked_at == "2026-07-10T21:00:00Z"


def test_install_from_requirements_locks_repository_relative_nested_skill_path() -> (
    None
):
    index = registered_skill_index(name="platform-skills")
    skill = installable_skill(
        name="runtime-verification",
        path="browser/runtime-verification",
        skill_file="browser/runtime-verification/SKILL.md",
        source_root="skills",
    )
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (skill,)},
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(
                    name="platform-skills/browser/runtime-verification",
                    target="claude",
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    result = use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == [
        (
            FakeSkillSourceResolver().source,
            skill,
            ".claude/skills/runtime-verification",
            False,
        ),
    ]
    entry = result.lockfile_entries[0]
    assert entry.requirement == "platform-skills/browser/runtime-verification"
    assert entry.skill_name == "runtime-verification"
    assert entry.skill_path == "skills/browser/runtime-verification"
    assert entry.skill_file == "skills/browser/runtime-verification/SKILL.md"


def test_install_from_requirements_expands_folder_prefix_to_matching_skills() -> None:
    index = registered_skill_index(name="platform-skills")
    code_review = installable_skill(
        name="code-review",
        path="software-development/code-review",
        skill_file="software-development/code-review/SKILL.md",
    )
    test_driven = installable_skill(
        name="test-driven-development",
        path="software-development/test-driven-development",
        skill_file="software-development/test-driven-development/SKILL.md",
    )
    other_skill = installable_skill(
        name="query-helper",
        path="data/query-helper",
        skill_file="data/query-helper/SKILL.md",
    )
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (test_driven, other_skill, code_review),
        },
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"agents": ".agents/skills"},
            skills=(
                SkillRequirement(
                    name="platform-skills/software-development",
                    target="agents",
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    result = use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == [
        (
            FakeSkillSourceResolver().source,
            code_review,
            ".agents/skills/code-review",
            False,
        ),
        (
            FakeSkillSourceResolver().source,
            test_driven,
            ".agents/skills/test-driven-development",
            False,
        ),
    ]
    assert [entry.requirement for entry in result.lockfile_entries] == [
        "platform-skills/software-development/code-review",
        "platform-skills/software-development/test-driven-development",
    ]
    assert [entry.target for entry in result.lockfile_entries] == [
        ".agents/skills/code-review",
        ".agents/skills/test-driven-development",
    ]
    assert result.installed_count == 2


def test_install_from_requirements_uses_target_path_exactly() -> None:
    index = registered_skill_index(name="platform-skills")
    skill = installable_skill(name="code-review")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (skill,)},
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={},
            skills=(
                SkillRequirement(
                    name="platform-skills/code-review",
                    target_path="../shared-agent-skills/review",
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    result = use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls[0][2] == "../shared-agent-skills/review"
    assert result.lockfile_entries[0].target == "../shared-agent-skills/review"
    assert result.lockfile_entries[0].target_ref is None


def test_skill_requirement_requires_exactly_one_target_selector() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        SkillRequirement(name="platform-skills/code-review")

    with pytest.raises(ValueError, match="exactly one"):
        SkillRequirement(
            name="platform-skills/code-review",
            target="claude",
            target_path=".claude/skills/code-review",
        )


def test_install_from_requirements_rejects_undefined_target_before_copy() -> None:
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"agents": ".agents/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = _use_case(reader=reader, installer=installer, manifest=manifest)

    with pytest.raises(UndefinedInstallTargetError, match="target nickname claude"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []
    assert manifest.lockfile_write_calls == []


def test_requirements_install_verifies_source_before_trusting_cached_metadata() -> None:
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (installable_skill(),)},
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallFromRequirements(
        requirements_reader=reader,
        catalog=catalog,
        source_resolver=FakeSkillSourceResolver(
            failure=SkillSourceResolutionError("bound commit index mismatch"),
        ),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(SkillSourceResolutionError, match="index mismatch"):
        use_case.execute(InstallFromRequirementsCommand())

    assert catalog.read_skills_calls == []
    assert installer.install_calls == []
    assert manifest.lockfile_write_calls == []


def test_install_from_requirements_rejects_duplicate_requirements_before_copy() -> None:
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
                SkillRequirement(
                    name="platform-skills/code-review",
                    target_path=".agents/skills/code-review",
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, installer=installer)

    with pytest.raises(
        DuplicateSkillRequirementError,
        match="platform-skills/code-review",
    ):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_install_from_requirements_rejects_duplicate_targets_before_copy() -> None:
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (
                installable_skill(name="code-review"),
                installable_skill(name="test-driven-development"),
            ),
        },
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={},
            skills=(
                SkillRequirement(
                    name="platform-skills/code-review",
                    target_path=".claude/skills/shared",
                ),
                SkillRequirement(
                    name="platform-skills/test-driven-development",
                    target_path=".claude/skills/shared",
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    with pytest.raises(DuplicateInstallTargetError, match=r"\.claude/skills/shared"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_install_from_requirements_rejects_canonically_equivalent_targets_before_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (
                installable_skill(name="code-review"),
                installable_skill(name="test-driven-development"),
            ),
        },
    )
    shared_target = tmp_path / "targets" / "shared"
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={},
            skills=(
                SkillRequirement(
                    name="platform-skills/code-review",
                    target_path="targets/./shared",
                ),
                SkillRequirement(
                    name="platform-skills/test-driven-development",
                    target_path=str(shared_target.parent / "nested" / ".." / "shared"),
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    with pytest.raises(DuplicateInstallTargetError, match="shared"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_install_from_requirements_rejects_parent_child_targets_before_copy(
    tmp_path: Path,
) -> None:
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (
                installable_skill(name="code-review"),
                installable_skill(name="test-driven-development"),
            ),
        },
    )
    parent = tmp_path / "targets" / "shared"
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={},
            skills=(
                SkillRequirement(
                    name="platform-skills/code-review",
                    target_path=str(parent),
                ),
                SkillRequirement(
                    name="platform-skills/test-driven-development",
                    target_path=str(parent / "nested"),
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    with pytest.raises(DuplicateInstallTargetError, match="nested"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_install_from_requirements_allows_canonical_sibling_targets(
    tmp_path: Path,
) -> None:
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (
                installable_skill(name="code-review"),
                installable_skill(name="test-driven-development"),
            ),
        },
    )
    target_parent = tmp_path / "targets"
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={},
            skills=(
                SkillRequirement(
                    name="platform-skills/code-review",
                    target_path=str(target_parent / "code-review"),
                ),
                SkillRequirement(
                    name="platform-skills/test-driven-development",
                    target_path=str(target_parent / "test-driven-development"),
                ),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    use_case.execute(InstallFromRequirementsCommand())

    assert len(installer.install_calls) == 2


def test_install_from_requirements_fails_unknown_index_before_copy() -> None:
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="missing-index/code-review", target="claude"),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, installer=installer)

    with pytest.raises(UnknownInstallIndexError, match="missing-index"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_install_from_requirements_fails_unknown_skill_before_copy() -> None:
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (installable_skill(name="other-skill"),),
        },
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    with pytest.raises(UnknownInstallSkillError, match="platform-skills/code-review"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_install_from_requirements_does_not_resolve_nested_skill_by_name() -> None:
    index = registered_skill_index(name="platform-skills")
    nested = installable_skill(
        name="code-review",
        path="software-development/code-review",
        skill_file="software-development/code-review/SKILL.md",
    )
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (nested,)},
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    with pytest.raises(
        UnknownInstallSkillError,
        match="platform-skills/code-review",
    ):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_install_from_requirements_passes_force_to_all_installs() -> None:
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (installable_skill(name="code-review"),),
        },
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )
    installer = FakeSkillInstaller()
    use_case = _use_case(reader=reader, catalog=catalog, installer=installer)

    use_case.execute(InstallFromRequirementsCommand(force=True))

    assert installer.install_calls[0][3] is True


def test_install_from_requirements_does_not_write_lockfile_when_first_copy_fails() -> (
    None
):
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (installable_skill(name="code-review"),),
        },
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )
    manifest = FakeInstallationManifest()
    installer = FakeSkillInstaller(
        ExistingInstallTargetError(".claude/skills/code-review"),
    )
    use_case = _use_case(
        reader=reader,
        catalog=catalog,
        installer=installer,
        manifest=manifest,
    )

    with pytest.raises(ExistingInstallTargetError):
        use_case.execute(InstallFromRequirementsCommand())

    assert manifest.lockfile_write_calls == []


def test_install_from_requirements_reports_partial_copy_without_lockfile_write() -> (
    None
):
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (
                installable_skill(name="code-review"),
                installable_skill(name="test-driven-development"),
            ),
        },
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
                SkillRequirement(
                    name="platform-skills/test-driven-development",
                    target="claude",
                ),
            ),
        ),
    )
    manifest = FakeInstallationManifest()
    installer = _FailOnSecondInstall()
    use_case = _use_case(
        reader=reader,
        catalog=catalog,
        installer=installer,
        manifest=manifest,
    )

    with pytest.raises(
        PartialInstallationError,
        match=r"ritebook\.lock was not updated",
    ):
        use_case.execute(InstallFromRequirementsCommand())

    assert len(installer.install_calls) == 2
    assert manifest.lockfile_write_calls == []


def test_install_from_requirements_rejects_naive_clock_before_copy() -> None:
    index = registered_skill_index(name="platform-skills")
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallFromRequirements(
        requirements_reader=_single_requirement_reader(),
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []
    assert manifest.lockfile_validate_calls == []
    assert manifest.lockfile_write_calls == []


def test_install_from_requirements_rejects_lockfile_validation_before_copy() -> None:
    index = registered_skill_index(name="platform-skills")
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest(
        validation_failure=InstallationPersistenceError("unsafe lockfile source"),
    )
    use_case = _use_case(
        reader=_single_requirement_reader(),
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        installer=installer,
        manifest=manifest,
    )

    with pytest.raises(InstallationPersistenceError, match="unsafe lockfile"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []
    assert manifest.lockfile_write_calls == []


def test_install_from_requirements_rejects_local_source_before_copy() -> None:
    index = registered_skill_index(
        name="platform-skills",
        source="/Users/example/internal-skills",
        source_type="local_git_repo",
        source_cache_path=None,
    )
    installer = FakeSkillInstaller()
    source_resolver = FakeSkillSourceResolver(
        ResolvedSkillSource(
            source=index.source,
            source_type=index.source_type,
            repository_path=index.source,
            source_revision=index.source_revision,
            index_digest=index.index_digest,
        ),
    )
    use_case = InstallFromRequirements(
        requirements_reader=_single_requirement_reader(),
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        source_resolver=source_resolver,
        installer=installer,
        manifest=JsonLockfileAdapter(),
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(InstallationPersistenceError, match="Git URL"):
        use_case.execute(InstallFromRequirementsCommand())

    assert installer.install_calls == []


def test_requirements_install_reports_retained_targets_on_lockfile_failure() -> None:
    index = registered_skill_index(name="platform-skills")
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest(
        write_failure=InstallationPersistenceError("lockfile cannot be written"),
    )
    use_case = _use_case(
        reader=_single_requirement_reader(),
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        installer=installer,
        manifest=manifest,
    )

    with pytest.raises(
        GeneratedStateCommitError,
        match=r"ritebook\.lock was not updated.*inspect.*retry",
    ):
        use_case.execute(InstallFromRequirementsCommand())

    assert len(installer.install_calls) == 1
    assert len(manifest.lockfile_write_calls) == 1


def test_requirements_install_tracks_target_after_cleanup_failure() -> None:
    index = registered_skill_index(name="platform-skills")
    installer = FakeSkillInstaller(
        failure=InstalledTargetCleanupError(
            target=".claude/skills/code-review",
            backup_path=".claude/skills/.code-review-backup/previous",
        ),
    )
    manifest = FakeInstallationManifest()
    use_case = _use_case(
        reader=_single_requirement_reader(),
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        installer=installer,
        manifest=manifest,
    )

    with pytest.raises(
        PartialInstallationError,
        match=(
            r"\.claude/skills/code-review.*ritebook\.lock was not updated"
            r".*backup.*remove backup"
        ),
    ):
        use_case.execute(InstallFromRequirementsCommand())

    assert len(installer.install_calls) == 1
    assert manifest.lockfile_write_calls == []


def test_install_from_requirements_sorts_lockfile_entries() -> None:
    platform = registered_skill_index(
        name="platform-skills",
        cached_index_path="/cache/indexes/platform-skills/ritebook-index.json",
    )
    company = registered_skill_index(
        name="company-skills",
        cached_index_path="/cache/indexes/company-skills/ritebook-index.json",
    )
    platform_skill = installable_skill(
        name="zeta-skill",
        path="zeta-skill",
        skill_file="zeta-skill/SKILL.md",
    )
    company_skill = installable_skill(
        name="alpha-skill",
        path="alpha-skill",
        skill_file="alpha-skill/SKILL.md",
    )
    catalog = FakeSkillCatalog(
        indexes=[platform, company],
        skills_by_path={
            platform.cached_index_path: (platform_skill,),
            company.cached_index_path: (company_skill,),
        },
    )
    reader = FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/zeta-skill", target="claude"),
                SkillRequirement(name="company-skills/alpha-skill", target="claude"),
            ),
        ),
    )
    use_case = _use_case(reader=reader, catalog=catalog)

    result = use_case.execute(InstallFromRequirementsCommand())

    assert [entry.requirement for entry in result.lockfile_entries] == [
        "company-skills/alpha-skill",
        "platform-skills/zeta-skill",
    ]


class _FailOnSecondInstall(FakeSkillInstaller):
    def install(
        self,
        *,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
        target: str,
        force: bool,
    ) -> None:
        super().install(source=source, skill=skill, target=target, force=force)
        if len(self.install_calls) == 2:
            raise ExistingInstallTargetError(target)


def _single_requirement_reader() -> FakeRequirementsReader:
    return FakeRequirementsReader(
        SkillRequirements(
            targets={"claude": ".claude/skills"},
            skills=(
                SkillRequirement(name="platform-skills/code-review", target="claude"),
            ),
        ),
    )


def _use_case(
    *,
    reader: FakeRequirementsReader,
    catalog: FakeSkillCatalog | None = None,
    installer: FakeSkillInstaller | None = None,
    manifest: FakeInstallationManifest | None = None,
) -> InstallFromRequirements:
    return InstallFromRequirements(
        requirements_reader=reader,
        catalog=catalog or FakeSkillCatalog(),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer or FakeSkillInstaller(),
        manifest=manifest or FakeInstallationManifest(),
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )
