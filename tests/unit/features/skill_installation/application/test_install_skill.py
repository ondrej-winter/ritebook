from datetime import UTC, datetime

import pytest

from ritebook.features.skill_installation.application.dtos import (
    InstallSkillCommand,
    SkillReference,
)
from ritebook.features.skill_installation.application.errors import (
    ConflictingRecordedTargetError,
    ExistingInstallTargetError,
    GeneratedStateCommitError,
    InstallationPersistenceError,
    InstalledTargetCleanupError,
    InvalidSkillReferenceError,
    SkillSourceResolutionError,
    UnknownInstallIndexError,
    UnknownInstallSkillError,
)
from ritebook.features.skill_installation.application.use_cases import InstallSkill

from .fakes import (
    FakeInstallationManifest,
    FakeSkillCatalog,
    FakeSkillInstaller,
    FakeSkillSourceResolver,
    installable_skill,
    registered_skill_index,
)


def test_skill_reference_parses_index_and_skill_names() -> None:
    reference = SkillReference.parse("platform-skills/code-review")

    assert reference.index_name == "platform-skills"
    assert reference.skill_path == "code-review"
    assert reference.skill_name == "code-review"
    assert reference.requirement == "platform-skills/code-review"


def test_skill_reference_parses_nested_skill_paths() -> None:
    reference = SkillReference.parse("platform-skills/browser/runtime-verification")

    assert reference.index_name == "platform-skills"
    assert reference.skill_path == "browser/runtime-verification"
    assert reference.skill_name == "runtime-verification"
    assert reference.requirement == "platform-skills/browser/runtime-verification"


@pytest.mark.parametrize(
    "skill_reference",
    [
        "platform-skills/CodeReview",
        "platform-skills/quality_tools/code-review",
        "platform-skills/quality/python/code-review",
    ],
)
def test_skill_reference_rejects_invalid_catalog_selectors(
    skill_reference: str,
) -> None:
    with pytest.raises(ValueError, match="Catalog path"):
        SkillReference.parse(skill_reference)


def test_skill_reference_rejects_invalid_index_names() -> None:
    with pytest.raises(ValueError, match="Local alias"):
        SkillReference.parse("InvalidIndex/code-review")


@pytest.mark.parametrize(
    "skill_reference",
    [
        "platform-skills//code-review",
        "platform-skills/code-review/",
        "platform-skills/../code-review",
        "platform-skills/browser/../code-review",
        "platform-skills/browser\\code-review",
    ],
)
def test_skill_reference_rejects_unsafe_skill_paths(skill_reference: str) -> None:
    with pytest.raises(ValueError, match="Catalog path"):
        SkillReference.parse(skill_reference)


def test_install_skill_command_requires_qualified_reference() -> None:
    with pytest.raises(ValueError, match="fully qualified"):
        InstallSkillCommand(skill_reference="code-review", target=".claude/skills")


def test_install_skill_command_requires_explicit_target() -> None:
    with pytest.raises(ValueError, match="Target must not be empty"):
        InstallSkillCommand(skill_reference="platform-skills/code-review", target="")


def test_install_skill_installs_selected_skill_and_writes_manifest() -> None:
    index = registered_skill_index(name="platform-skills")
    skill = installable_skill()
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (skill,)},
    )
    source_resolver = FakeSkillSourceResolver()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=source_resolver,
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    result = use_case.execute(
        InstallSkillCommand(
            skill_reference="platform-skills/code-review",
            target=".claude/skills/code-review",
            registry_path="/tmp/indexes.json",
            installation_registry_path="/tmp/installations.json",
        ),
    )

    assert result.requirement == "platform-skills/code-review"
    assert result.target == ".claude/skills/code-review"
    assert catalog.get_index_calls == [("platform-skills", "/tmp/indexes.json")]
    assert catalog.read_skills_calls == [index.cached_index_path]
    assert source_resolver.resolve_calls == [index]
    assert installer.install_calls == [
        (
            source_resolver.source,
            skill,
            ".claude/skills/code-review",
            False,
        ),
    ]
    assert manifest.write_calls == [
        (result.manifest_entry, "/tmp/installations.json", False),
    ]
    assert result.manifest_entry.installed_at == "2026-07-10T21:00:00Z"
    assert result.manifest_entry.source_revision == "c" * 40
    assert result.manifest_entry.skill_path == "skills/code-review"
    assert result.manifest_entry.skill_file == "skills/code-review/SKILL.md"


def test_install_skill_records_repository_relative_nested_skill_path() -> None:
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
    installer = FakeSkillInstaller()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=FakeInstallationManifest(),
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    result = use_case.execute(
        InstallSkillCommand(
            skill_reference="platform-skills/browser/runtime-verification",
            target=".claude/skills/runtime-verification",
        ),
    )

    assert installer.install_calls[0][1] == skill
    assert result.manifest_entry.requirement == (
        "platform-skills/browser/runtime-verification"
    )
    assert result.manifest_entry.skill_name == "runtime-verification"
    assert result.manifest_entry.skill_path == "skills/browser/runtime-verification"
    assert result.manifest_entry.skill_file == (
        "skills/browser/runtime-verification/SKILL.md"
    )


def test_install_skill_resolves_duplicate_names_by_exact_path() -> None:
    index = registered_skill_index(name="platform-skills")
    backend = installable_skill(
        name="code-review",
        path="backend/code-review",
        skill_file="backend/code-review/SKILL.md",
    )
    frontend = installable_skill(
        name="code-review",
        path="frontend/code-review",
        skill_file="frontend/code-review/SKILL.md",
    )
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (backend, frontend)},
    )
    installer = FakeSkillInstaller()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=FakeInstallationManifest(),
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    use_case.execute(
        InstallSkillCommand(
            skill_reference="platform-skills/frontend/code-review",
            target=".claude/skills/code-review",
        ),
    )

    assert installer.install_calls[0][1] == frontend


def test_install_skill_does_not_resolve_nested_skill_by_name() -> None:
    index = registered_skill_index(name="platform-skills")
    nested = installable_skill(
        name="code-review",
        path="software-development/code-review",
        skill_file="software-development/code-review/SKILL.md",
    )
    installer = FakeSkillInstaller()
    use_case = InstallSkill(
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (nested,)},
        ),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=FakeInstallationManifest(),
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(
        UnknownInstallSkillError,
        match="platform-skills/code-review",
    ):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="platform-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert installer.install_calls == []


def test_install_skill_does_not_expand_collection_selector() -> None:
    index = registered_skill_index(name="platform-skills")
    collection_child = installable_skill(
        name="runtime-verification",
        path="browser/runtime-verification",
        skill_file="browser/runtime-verification/SKILL.md",
    )
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (collection_child,)},
        ),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(
        UnknownInstallSkillError,
        match="platform-skills/browser",
    ):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="platform-skills/browser",
                target=".claude/skills/browser",
            ),
        )

    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_rejects_malformed_reference_before_lookup() -> None:
    catalog = FakeSkillCatalog()
    source_resolver = FakeSkillSourceResolver()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=source_resolver,
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(InvalidSkillReferenceError, match="fully qualified"):
        use_case.execute(
            _invalid_install_command("code-review"),
        )

    assert catalog.get_index_calls == []
    assert source_resolver.resolve_calls == []
    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_rejects_over_deep_selector_before_lookup() -> None:
    catalog = FakeSkillCatalog()
    source_resolver = FakeSkillSourceResolver()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=source_resolver,
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(InvalidSkillReferenceError, match="one or two segments"):
        use_case.execute(
            _invalid_install_command(
                "platform-skills/quality/python/code-review",
            ),
        )

    assert catalog.get_index_calls == []
    assert source_resolver.resolve_calls == []
    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_fails_for_unknown_index_before_copy() -> None:
    catalog = FakeSkillCatalog()
    source_resolver = FakeSkillSourceResolver()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=source_resolver,
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(
        UnknownInstallIndexError,
        match="unknown local alias: missing-index",
    ):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="missing-index/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert catalog.read_skills_calls == []
    assert source_resolver.resolve_calls == []
    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_verifies_source_before_trusting_cached_metadata() -> None:
    index = registered_skill_index(name="platform-skills")
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (installable_skill(),)},
    )
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=FakeSkillSourceResolver(
            failure=SkillSourceResolutionError("cached index digest mismatch"),
        ),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(SkillSourceResolutionError, match="digest mismatch"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="platform-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert catalog.read_skills_calls == []
    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_fails_for_unknown_skill_after_source_verification() -> None:
    index = registered_skill_index()
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={
            index.cached_index_path: (installable_skill(name="other-skill"),),
        },
    )
    source_resolver = FakeSkillSourceResolver()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=source_resolver,
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(UnknownInstallSkillError, match="company-skills/code-review"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="company-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert source_resolver.resolve_calls == [index]
    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_surfaces_target_refusal_without_manifest_write() -> None:
    index = registered_skill_index()
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (installable_skill(),)},
    )
    installer = FakeSkillInstaller(
        ExistingInstallTargetError(".claude/skills/code-review"),
    )
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(ExistingInstallTargetError, match="use --force"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="company-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert installer.install_calls[0][3] is False
    assert manifest.write_calls == []


def test_install_skill_passes_force_to_installer_and_manifest_writer() -> None:
    index = registered_skill_index()
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (installable_skill(),)},
    )
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    use_case.execute(
        InstallSkillCommand(
            skill_reference="company-skills/code-review",
            target=".claude/skills/code-review",
            force=True,
        ),
    )

    assert installer.install_calls[0][3] is True
    assert manifest.write_calls[0][2] is True


def test_install_skill_rejects_naive_clock_values_before_copy() -> None:
    index = registered_skill_index()
    catalog = FakeSkillCatalog(
        indexes=[index],
        skills_by_path={index.cached_index_path: (installable_skill(),)},
    )
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=catalog,
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="company-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_rejects_manifest_validation_before_copy() -> None:
    index = registered_skill_index()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest(
        validation_failure=InstallationPersistenceError("registry is malformed"),
    )
    use_case = InstallSkill(
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(InstallationPersistenceError, match="malformed"):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="company-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert installer.install_calls == []
    assert manifest.write_calls == []


def test_install_skill_reports_retained_target_when_manifest_commit_fails() -> None:
    index = registered_skill_index()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest(
        write_failure=InstallationPersistenceError("registry cannot be written"),
    )
    use_case = InstallSkill(
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(
        GeneratedStateCommitError,
        match=r"installations\.json was not updated.*inspect.*retry",
    ):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="company-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert len(installer.install_calls) == 1
    assert len(manifest.write_calls) == 1


def test_install_skill_reports_retained_target_on_post_copy_registry_conflict() -> None:
    index = registered_skill_index()
    installer = FakeSkillInstaller()
    manifest = FakeInstallationManifest(
        write_failure=ConflictingRecordedTargetError("registry changed"),
    )
    use_case = InstallSkill(
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(
        GeneratedStateCommitError,
        match=r"installations\.json was not updated.*inspect.*retry",
    ):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="company-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert len(installer.install_calls) == 1
    assert len(manifest.write_calls) == 1


def test_install_skill_preserves_backup_guidance_after_cleanup_failure() -> None:
    index = registered_skill_index()
    installer = FakeSkillInstaller(
        InstalledTargetCleanupError(
            target=".claude/skills/code-review",
            backup_path=".claude/skills/.code-review-backup/previous",
        ),
    )
    manifest = FakeInstallationManifest()
    use_case = InstallSkill(
        catalog=FakeSkillCatalog(
            indexes=[index],
            skills_by_path={index.cached_index_path: (installable_skill(),)},
        ),
        source_resolver=FakeSkillSourceResolver(),
        installer=installer,
        manifest=manifest,
        clock=lambda: datetime(2026, 7, 10, 21, 0, tzinfo=UTC),
    )

    with pytest.raises(
        GeneratedStateCommitError,
        match=r"installations\.json was not updated.*remove backup",
    ):
        use_case.execute(
            InstallSkillCommand(
                skill_reference="company-skills/code-review",
                target=".claude/skills/code-review",
            ),
        )

    assert len(installer.install_calls) == 1
    assert manifest.write_calls == []


def _invalid_install_command(skill_reference: str) -> InstallSkillCommand:
    command = object.__new__(InstallSkillCommand)
    object.__setattr__(command, "skill_reference", skill_reference)
    object.__setattr__(command, "target", ".claude/skills/code-review")
    object.__setattr__(command, "force", False)
    object.__setattr__(command, "registry_path", None)
    object.__setattr__(command, "installation_registry_path", None)
    return command
