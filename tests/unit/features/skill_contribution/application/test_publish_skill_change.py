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
    AmbiguousContributionSkillReferenceError,
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
        AmbiguousContributionSkillReferenceError,
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
