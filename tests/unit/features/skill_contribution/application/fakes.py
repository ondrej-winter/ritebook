from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionSkillReference,
    ContributionWorkspace,
    PreparedContribution,
    SkillChangeComparison,
    SkillChangeStatus,
)


class FakeContributionLockfile:
    def __init__(
        self,
        entry: ContributionLockfileEntry | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.entry = entry or contribution_lockfile_entry()
        self.failure = failure
        self.resolve_calls: list[tuple[ContributionSkillReference, str | None]] = []

    def resolve_entry(
        self,
        reference: ContributionSkillReference,
        lockfile_path: str | None,
    ) -> ContributionLockfileEntry:
        self.resolve_calls.append((reference, lockfile_path))
        if self.failure is not None:
            raise self.failure
        return self.entry


class FakeSkillSourceWorkspace:
    def __init__(
        self,
        workspace: ContributionWorkspace | None = None,
        failure: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.workspace = workspace or contribution_workspace()
        self.failure = failure
        self.events = events
        self.prepare_calls: list[tuple[ContributionLockfileEntry, str | None]] = []

    def prepare_workspace(
        self,
        entry: ContributionLockfileEntry,
        contribution_root: str | None,
    ) -> ContributionWorkspace:
        self.prepare_calls.append((entry, contribution_root))
        if self.events is not None:
            self.events.append("prepare_workspace")
        if self.failure is not None:
            raise self.failure
        return self.workspace


class FakeSkillChangeDetector:
    def __init__(
        self,
        comparison: SkillChangeComparison | None = None,
        failure: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.comparison = comparison or changed_comparison()
        self.failure = failure
        self.events = events
        self.compare_calls: list[
            tuple[ContributionLockfileEntry, ContributionWorkspace]
        ] = []

    def compare(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> SkillChangeComparison:
        self.compare_calls.append((entry, workspace))
        if self.events is not None:
            self.events.append("compare")
        if self.failure is not None:
            raise self.failure
        return self.comparison


class FakeContributionCheckout:
    def __init__(
        self,
        prepared: PreparedContribution | None = None,
        prepare_failure: Exception | None = None,
        commit_failure: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.prepared = prepared or prepared_contribution()
        self.prepare_failure = prepare_failure
        self.commit_failure = commit_failure
        self.events = events
        self.prepare_branch_calls: list[
            tuple[ContributionLockfileEntry, ContributionWorkspace]
        ] = []
        self.commit_changes_calls: list[
            tuple[ContributionLockfileEntry, ContributionWorkspace, str]
        ] = []

    def prepare_branch(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> str:
        self.prepare_branch_calls.append((entry, workspace))
        if self.events is not None:
            self.events.append("prepare_branch")
        if self.prepare_failure is not None:
            raise self.prepare_failure
        return self.prepared.branch_name

    def commit_changes(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
        branch_name: str,
    ) -> PreparedContribution:
        self.commit_changes_calls.append((entry, workspace, branch_name))
        if self.events is not None:
            self.events.append("commit_changes")
        if self.commit_failure is not None:
            raise self.commit_failure
        return self.prepared


class FakeSkillDirectory:
    def __init__(
        self,
        failure: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.failure = failure
        self.events = events
        self.copy_calls: list[
            tuple[ContributionLockfileEntry, ContributionWorkspace]
        ] = []

    def copy_installed_skill(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        self.copy_calls.append((entry, workspace))
        if self.events is not None:
            self.events.append("copy_installed_skill")
        if self.failure is not None:
            raise self.failure


class FakeSkillValidator:
    def __init__(
        self,
        failure: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.failure = failure
        self.events = events
        self.validate_calls: list[
            tuple[ContributionLockfileEntry, ContributionWorkspace]
        ] = []

    def validate(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        self.validate_calls.append((entry, workspace))
        if self.events is not None:
            self.events.append("validate")
        if self.failure is not None:
            raise self.failure


class FakeIndexRegenerator:
    def __init__(
        self,
        failure: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.failure = failure
        self.events = events
        self.regenerate_calls: list[
            tuple[ContributionLockfileEntry, ContributionWorkspace]
        ] = []

    def regenerate_index(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        self.regenerate_calls.append((entry, workspace))
        if self.events is not None:
            self.events.append("regenerate_index")
        if self.failure is not None:
            raise self.failure


def contribution_lockfile_entry(
    *,
    requirement: str = "platform-skills/code-review",
    index_name: str = "platform-skills",
    skill_name: str = "code-review",
    target: str = ".agents/skills/code-review",
    source: str = "git@example.com:example/skills.git",
    source_type: str = "git_url",
    source_revision: str = "abc123",
    skill_path: str = "skills/code-review",
    skill_file: str = "skills/code-review/SKILL.md",
    index_schema_version: int = 1,
) -> ContributionLockfileEntry:
    return ContributionLockfileEntry(
        requirement=requirement,
        index_name=index_name,
        skill_name=skill_name,
        target=target,
        source=source,
        source_type=source_type,
        source_revision=source_revision,
        skill_path=skill_path,
        skill_file=skill_file,
        index_schema_version=index_schema_version,
    )


def contribution_workspace() -> ContributionWorkspace:
    return ContributionWorkspace(
        checkout_path="/tmp/ritebook/contributions/platform-skills-code-review",
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )


def changed_comparison() -> SkillChangeComparison:
    return SkillChangeComparison(
        status=SkillChangeStatus.CHANGED,
        installed_path=".agents/skills/code-review",
        source_skill_path="skills/code-review",
        changed_file_count=2,
    )


def no_change_comparison() -> SkillChangeComparison:
    return SkillChangeComparison(
        status=SkillChangeStatus.NO_CHANGES,
        installed_path=".agents/skills/code-review",
        source_skill_path="skills/code-review",
    )


def upstream_changed_comparison() -> SkillChangeComparison:
    return SkillChangeComparison(
        status=SkillChangeStatus.UPSTREAM_CHANGED,
        installed_path=".agents/skills/code-review",
        source_skill_path="skills/code-review",
        changed_file_count=1,
    )


def prepared_contribution() -> PreparedContribution:
    return PreparedContribution(
        skill_reference="platform-skills/code-review",
        checkout_path="/tmp/ritebook/contributions/platform-skills-code-review",
        branch_name="ritebook/code-review-20260718201534",
        commit_hash="abc1234",
        push_command="git push origin ritebook/code-review-20260718201534",
    )
