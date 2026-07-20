import pytest

from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionSkillReference,
    ContributionWorkspace,
    PreparedContribution,
    PublishSkillChangeCommand,
    PublishSkillChangeResult,
    SkillChangeComparison,
    SkillChangeStatus,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionGitError,
    ContributionIndexRegenerationError,
    ContributionLockfileEntryNotFoundError,
    ContributionLockfileReadError,
    IncompleteContributionProvenanceError,
    InvalidContributionSkillReferenceError,
    MissingInstalledSkillTargetError,
    SkillContributionError,
    SkillContributionValidationError,
    UnsafeContributionPathError,
    UpstreamSkillChangedError,
)
from ritebook.features.skill_contribution.application.ports import (
    ContributionCheckoutPort,
    ContributionLockfilePort,
    IndexRegeneratorPort,
    PublishSkillChangePort,
    SkillChangeDetectorPort,
    SkillDirectoryPort,
    SkillSourceWorkspacePort,
    SkillValidatorPort,
)
from ritebook.features.skill_contribution.application.use_cases import (
    PublishSkillChange,
    PublishSkillChangeDependencies,
)

from .fakes import (
    FakeContributionCheckout,
    FakeContributionLockfile,
    FakeIndexRegenerator,
    FakeSkillChangeDetector,
    FakeSkillDirectory,
    FakeSkillSourceWorkspace,
    FakeSkillValidator,
    changed_comparison,
    no_change_comparison,
    upstream_changed_comparison,
)


def test_contribution_skill_reference_parses_flat_selector() -> None:
    reference = ContributionSkillReference.parse("platform-skills/code-review")

    assert reference.requirement == "platform-skills/code-review"
    assert reference.index_name == "platform-skills"
    assert reference.skill_selector == "code-review"
    assert reference.skill_name == "code-review"


def test_contribution_skill_reference_parses_nested_selector() -> None:
    reference = ContributionSkillReference.parse(
        "platform-skills/browser/runtime-verification",
    )

    assert reference.index_name == "platform-skills"
    assert reference.skill_selector == "browser/runtime-verification"
    assert reference.skill_name == "runtime-verification"


@pytest.mark.parametrize(
    "skill_reference",
    [
        "code-review",
        "InvalidIndex/code-review",
        "platform-skills//code-review",
        "platform-skills/code-review/",
        "platform-skills/../code-review",
        "platform-skills/browser/../code-review",
        "platform-skills/browser\\code-review",
    ],
)
def test_contribution_skill_reference_rejects_invalid_values(
    skill_reference: str,
) -> None:
    with pytest.raises(ValueError, match=r"Skill reference|Index name|Skill selector"):
        ContributionSkillReference.parse(skill_reference)


def test_publish_skill_change_command_validates_reference_and_overrides() -> None:
    command = PublishSkillChangeCommand(
        skill_reference="platform-skills/code-review",
        lockfile_path="custom.lock",
        contribution_root=".ritebook/contributions",
    )

    assert command.skill_reference == "platform-skills/code-review"
    assert command.lockfile_path == "custom.lock"
    assert command.contribution_root == ".ritebook/contributions"


@pytest.mark.parametrize("field", ["lockfile_path", "contribution_root"])
def test_publish_skill_change_command_rejects_empty_optional_paths(field: str) -> None:
    kwargs = {field: ""}

    with pytest.raises(ValueError, match="must not be empty"):
        PublishSkillChangeCommand(
            skill_reference="platform-skills/code-review",
            **kwargs,
        )


def test_contribution_lockfile_entry_requires_mvp_provenance() -> None:
    entry = contribution_lockfile_entry()

    assert entry.requirement == "platform-skills/code-review"
    assert entry.source_revision == "abc123"
    assert entry.skill_path == "skills/code-review"
    assert entry.skill_file == "skills/code-review/SKILL.md"


@pytest.mark.parametrize(
    "field",
    [
        "requirement",
        "index_name",
        "skill_name",
        "target",
        "source",
        "source_type",
        "source_revision",
        "skill_path",
        "skill_file",
    ],
)
def test_contribution_lockfile_entry_rejects_missing_required_fields(
    field: str,
) -> None:
    kwargs = _entry_kwargs()
    kwargs[field] = ""

    with pytest.raises(ValueError, match=r"must not be empty|Index name|Skill name"):
        ContributionLockfileEntry(**kwargs)


def test_contribution_lockfile_entry_rejects_unsafe_source_paths() -> None:
    kwargs = _entry_kwargs()
    kwargs["skill_path"] = "../skills/code-review"

    with pytest.raises(ValueError, match="safe relative POSIX path"):
        ContributionLockfileEntry(**kwargs)


def test_comparison_rejects_no_change_with_changed_file_count() -> None:
    with pytest.raises(ValueError, match="No-change"):
        SkillChangeComparison(
            status=SkillChangeStatus.NO_CHANGES,
            installed_path=".agents/skills/code-review",
            source_skill_path="skills/code-review",
            changed_file_count=1,
        )


def test_publish_result_allows_no_change_without_prepared_contribution() -> None:
    result = PublishSkillChangeResult(
        skill_reference="platform-skills/code-review",
        status=SkillChangeStatus.NO_CHANGES,
    )

    assert result.prepared_contribution is None


def test_publish_result_requires_prepared_contribution_for_changed_status() -> None:
    with pytest.raises(ValueError, match="prepared metadata"):
        PublishSkillChangeResult(
            skill_reference="platform-skills/code-review",
            status=SkillChangeStatus.CHANGED,
        )


def test_publish_result_rejects_prepared_contribution_for_no_change_status() -> None:
    with pytest.raises(ValueError, match="Only changed"):
        PublishSkillChangeResult(
            skill_reference="platform-skills/code-review",
            status=SkillChangeStatus.NO_CHANGES,
            prepared_contribution=prepared_contribution(),
        )


def test_publish_result_accepts_changed_result_with_prepared_metadata() -> None:
    prepared = prepared_contribution()
    result = PublishSkillChangeResult(
        skill_reference="platform-skills/code-review",
        status=SkillChangeStatus.CHANGED,
        prepared_contribution=prepared,
    )

    assert result.prepared_contribution == prepared


def test_user_facing_errors_share_base_type() -> None:
    error_types = (
        InvalidContributionSkillReferenceError,
        ContributionLockfileReadError,
        ContributionLockfileEntryNotFoundError,
        IncompleteContributionProvenanceError,
        MissingInstalledSkillTargetError,
        UpstreamSkillChangedError,
        SkillContributionValidationError,
        ContributionIndexRegenerationError,
        ContributionGitError,
        UnsafeContributionPathError,
    )

    for error_type in error_types:
        if error_type is UpstreamSkillChangedError:
            error = error_type()
        elif error_type is IncompleteContributionProvenanceError:
            error = error_type("platform-skills/code-review", "source_revision")
        else:
            error = error_type("safe user-facing message")
        assert isinstance(error, SkillContributionError)


def test_upstream_changed_error_includes_remediation_guidance() -> None:
    error = UpstreamSkillChangedError()

    assert "upstream changed since locked revision" in str(error)
    assert "reconcile" in str(error)


def test_port_protocols_are_importable() -> None:
    assert PublishSkillChangePort is not None
    assert ContributionLockfilePort is not None
    assert SkillSourceWorkspacePort is not None
    assert SkillChangeDetectorPort is not None
    assert SkillDirectoryPort is not None
    assert SkillValidatorPort is not None
    assert IndexRegeneratorPort is not None
    assert ContributionCheckoutPort is not None


def test_publish_skill_change_rejects_malformed_reference_before_lookup() -> None:
    lockfile = FakeContributionLockfile()
    use_case = publish_skill_change(lockfile=lockfile)

    with pytest.raises(InvalidContributionSkillReferenceError, match="fully qualified"):
        use_case.execute(_invalid_publish_command("code-review"))

    assert lockfile.resolve_calls == []


def test_publish_skill_change_resolves_lockfile_entry() -> None:
    lockfile = FakeContributionLockfile()
    use_case = publish_skill_change(lockfile=lockfile)

    use_case.execute(
        PublishSkillChangeCommand(
            skill_reference="platform-skills/code-review",
            lockfile_path="custom.lock",
        ),
    )

    [(reference, lockfile_path)] = lockfile.resolve_calls
    assert reference.requirement == "platform-skills/code-review"
    assert reference.index_name == "platform-skills"
    assert reference.skill_selector == "code-review"
    assert lockfile_path == "custom.lock"


def test_publish_skill_change_surfaces_missing_lockfile_entry_before_checkout() -> None:
    failure = ContributionLockfileEntryNotFoundError(
        "no lockfile entry found for platform-skills/code-review",
    )
    lockfile = FakeContributionLockfile(failure=failure)
    source_workspace = FakeSkillSourceWorkspace()
    use_case = publish_skill_change(
        lockfile=lockfile,
        source_workspace=source_workspace,
    )

    with pytest.raises(ContributionLockfileEntryNotFoundError, match="no lockfile"):
        use_case.execute(publish_command())

    assert source_workspace.prepare_calls == []


def test_publish_skill_change_rejects_incomplete_provenance_before_checkout() -> None:
    entry = incomplete_entry(source_revision="")
    lockfile = FakeContributionLockfile(entry=entry)
    source_workspace = FakeSkillSourceWorkspace()
    use_case = publish_skill_change(
        lockfile=lockfile,
        source_workspace=source_workspace,
    )

    with pytest.raises(IncompleteContributionProvenanceError, match="source_revision"):
        use_case.execute(publish_command())

    assert source_workspace.prepare_calls == []


def test_publish_skill_change_surfaces_missing_installed_target_before_branch() -> None:
    failure = MissingInstalledSkillTargetError(
        "installed skill target .agents/skills/code-review does not exist",
    )
    change_detector = FakeSkillChangeDetector(failure=failure)
    checkout = FakeContributionCheckout()
    use_case = publish_skill_change(
        change_detector=change_detector,
        checkout=checkout,
    )

    with pytest.raises(MissingInstalledSkillTargetError, match="does not exist"):
        use_case.execute(publish_command())

    assert checkout.prepare_branch_calls == []
    assert checkout.commit_changes_calls == []


def test_publish_skill_change_fails_for_upstream_changes_before_copy() -> None:
    change_detector = FakeSkillChangeDetector(comparison=upstream_changed_comparison())
    checkout = FakeContributionCheckout()
    skill_directory = FakeSkillDirectory()
    validator = FakeSkillValidator()
    index_regenerator = FakeIndexRegenerator()
    use_case = publish_skill_change(
        change_detector=change_detector,
        checkout=checkout,
        skill_directory=skill_directory,
        validator=validator,
        index_regenerator=index_regenerator,
    )

    with pytest.raises(UpstreamSkillChangedError, match="upstream changed"):
        use_case.execute(publish_command())

    assert checkout.prepare_branch_calls == []
    assert skill_directory.copy_calls == []
    assert validator.validate_calls == []
    assert index_regenerator.regenerate_calls == []
    assert checkout.commit_changes_calls == []


def test_publish_skill_change_returns_noop_without_branch_or_commit() -> None:
    change_detector = FakeSkillChangeDetector(comparison=no_change_comparison())
    checkout = FakeContributionCheckout()
    skill_directory = FakeSkillDirectory()
    validator = FakeSkillValidator()
    index_regenerator = FakeIndexRegenerator()
    use_case = publish_skill_change(
        change_detector=change_detector,
        checkout=checkout,
        skill_directory=skill_directory,
        validator=validator,
        index_regenerator=index_regenerator,
    )

    result = use_case.execute(publish_command())

    assert result.skill_reference == "platform-skills/code-review"
    assert result.status is SkillChangeStatus.NO_CHANGES
    assert result.prepared_contribution is None
    assert checkout.prepare_branch_calls == []
    assert skill_directory.copy_calls == []
    assert validator.validate_calls == []
    assert index_regenerator.regenerate_calls == []
    assert checkout.commit_changes_calls == []


def test_publish_skill_change_runs_changed_workflow_in_order() -> None:
    events: list[str] = []
    checkout = FakeContributionCheckout(events=events)
    use_case = publish_skill_change(
        source_workspace=FakeSkillSourceWorkspace(events=events),
        change_detector=FakeSkillChangeDetector(events=events),
        checkout=checkout,
        skill_directory=FakeSkillDirectory(events=events),
        validator=FakeSkillValidator(events=events),
        index_regenerator=FakeIndexRegenerator(events=events),
    )

    result = use_case.execute(
        PublishSkillChangeCommand(
            skill_reference="platform-skills/code-review",
            contribution_root=".ritebook/contributions",
        ),
    )

    assert events == [
        "prepare_workspace",
        "compare",
        "prepare_branch",
        "copy_installed_skill",
        "validate",
        "regenerate_index",
        "commit_changes",
    ]
    assert result.status is SkillChangeStatus.CHANGED
    assert result.prepared_contribution == checkout.prepared
    assert result.prepared_contribution.checkout_path == checkout.prepared.checkout_path
    assert result.prepared_contribution.branch_name == checkout.prepared.branch_name
    assert result.prepared_contribution.commit_hash == checkout.prepared.commit_hash
    assert result.prepared_contribution.push_command == checkout.prepared.push_command


def test_publish_skill_change_validation_failure_prevents_regeneration_and_commit() -> (
    None
):
    failure = SkillContributionValidationError(
        "skill validation failed; contribution commit was not created",
    )
    index_regenerator = FakeIndexRegenerator()
    checkout = FakeContributionCheckout()
    use_case = publish_skill_change(
        checkout=checkout,
        validator=FakeSkillValidator(failure=failure),
        index_regenerator=index_regenerator,
    )

    with pytest.raises(SkillContributionValidationError, match="validation failed"):
        use_case.execute(publish_command())

    assert index_regenerator.regenerate_calls == []
    assert checkout.commit_changes_calls == []


def test_publish_skill_change_index_failure_prevents_commit() -> None:
    failure = ContributionIndexRegenerationError(
        "failed to regenerate ritebook-index.json",
    )
    checkout = FakeContributionCheckout()
    use_case = publish_skill_change(
        checkout=checkout,
        index_regenerator=FakeIndexRegenerator(failure=failure),
    )

    with pytest.raises(ContributionIndexRegenerationError, match="regenerate"):
        use_case.execute(publish_command())

    assert checkout.commit_changes_calls == []


def test_publish_skill_change_returns_prepared_contribution_metadata() -> None:
    prepared = prepared_contribution()
    use_case = publish_skill_change(
        checkout=FakeContributionCheckout(prepared=prepared),
    )

    result = use_case.execute(publish_command())

    assert result.status is SkillChangeStatus.CHANGED
    assert result.prepared_contribution == prepared


def contribution_lockfile_entry() -> ContributionLockfileEntry:
    return ContributionLockfileEntry(**_entry_kwargs())


def contribution_workspace() -> ContributionWorkspace:
    return ContributionWorkspace(
        checkout_path="/tmp/ritebook/contributions/platform-skills-code-review",
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )


def prepared_contribution() -> PreparedContribution:
    return PreparedContribution(
        skill_reference="platform-skills/code-review",
        checkout_path="/tmp/ritebook/contributions/platform-skills-code-review",
        branch_name="ritebook/code-review-20260718201534",
        commit_hash="abc1234",
        push_command="git push origin ritebook/code-review-20260718201534",
    )


def _entry_kwargs() -> dict[str, object]:
    return {
        "requirement": "platform-skills/code-review",
        "index_name": "platform-skills",
        "skill_name": "code-review",
        "target": ".agents/skills/code-review",
        "source": "git@example.com:example/skills.git",
        "source_type": "git_url",
        "source_revision": "abc123",
        "skill_path": "skills/code-review",
        "skill_file": "skills/code-review/SKILL.md",
        "index_schema_version": 1,
    }


def publish_command() -> PublishSkillChangeCommand:
    return PublishSkillChangeCommand(skill_reference="platform-skills/code-review")


def publish_skill_change(
    *,
    lockfile: FakeContributionLockfile | None = None,
    source_workspace: FakeSkillSourceWorkspace | None = None,
    change_detector: FakeSkillChangeDetector | None = None,
    checkout: FakeContributionCheckout | None = None,
    skill_directory: FakeSkillDirectory | None = None,
    validator: FakeSkillValidator | None = None,
    index_regenerator: FakeIndexRegenerator | None = None,
) -> PublishSkillChange:
    return PublishSkillChange(
        PublishSkillChangeDependencies(
            lockfile=lockfile or FakeContributionLockfile(),
            source_workspace=source_workspace or FakeSkillSourceWorkspace(),
            change_detector=change_detector
            or FakeSkillChangeDetector(
                comparison=changed_comparison(),
            ),
            checkout=checkout or FakeContributionCheckout(),
            skill_directory=skill_directory or FakeSkillDirectory(),
            validator=validator or FakeSkillValidator(),
            index_regenerator=index_regenerator or FakeIndexRegenerator(),
        ),
    )


def _invalid_publish_command(skill_reference: str) -> PublishSkillChangeCommand:
    command = object.__new__(PublishSkillChangeCommand)
    object.__setattr__(command, "skill_reference", skill_reference)
    object.__setattr__(command, "lockfile_path", None)
    object.__setattr__(command, "contribution_root", None)
    return command


def incomplete_entry(**overrides: object) -> ContributionLockfileEntry:
    entry = object.__new__(ContributionLockfileEntry)
    values = _entry_kwargs() | overrides
    for field_name, value in values.items():
        object.__setattr__(entry, field_name, value)
    return entry
