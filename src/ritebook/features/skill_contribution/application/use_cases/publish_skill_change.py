"""Publish-skill-change application use case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ritebook.features.skill_contribution.application.dtos import (
    ContributionSkillReference,
    PublishSkillChangeCommand,
    PublishSkillChangeResult,
    SkillChangeStatus,
)
from ritebook.features.skill_contribution.application.errors import (
    IncompleteContributionProvenanceError,
    InvalidContributionSkillReferenceError,
    UpstreamSkillChangedError,
)
from ritebook.features.skill_contribution.application.ports import (
    PublishSkillChangePort,
)

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.ports import (
        ContributionCheckoutPort,
        ContributionLockfilePort,
        IndexRegeneratorPort,
        SkillChangeDetectorPort,
        SkillDirectoryPort,
        SkillSourceWorkspacePort,
        SkillValidatorPort,
    )


@dataclass(frozen=True)
class PublishSkillChangeDependencies:
    """Ports required to orchestrate skill contribution publishing."""

    lockfile: ContributionLockfilePort
    source_workspace: SkillSourceWorkspacePort
    change_detector: SkillChangeDetectorPort
    checkout: ContributionCheckoutPort
    skill_directory: SkillDirectoryPort
    validator: SkillValidatorPort
    index_regenerator: IndexRegeneratorPort


class PublishSkillChange(PublishSkillChangePort):
    """Prepare one installed skill change for upstream review."""

    def __init__(self, dependencies: PublishSkillChangeDependencies) -> None:
        """Initialize contribution orchestration dependencies."""
        self._dependencies = dependencies

    def execute(self, command: PublishSkillChangeCommand) -> PublishSkillChangeResult:
        """Resolve, compare, validate, regenerate, and commit one contribution."""
        try:
            reference = ContributionSkillReference.parse(command.skill_reference)
        except ValueError as err:
            raise InvalidContributionSkillReferenceError(str(err)) from err

        entry = self._dependencies.lockfile.resolve_entry(
            reference,
            command.lockfile_path,
        )
        self._validate_required_provenance(entry, reference.requirement)
        workspace = self._dependencies.source_workspace.prepare_workspace(
            entry,
            command.contribution_root,
        )
        comparison = self._dependencies.change_detector.compare(entry, workspace)

        if comparison.status is SkillChangeStatus.UPSTREAM_CHANGED:
            raise UpstreamSkillChangedError
        if comparison.status is SkillChangeStatus.NO_CHANGES:
            return PublishSkillChangeResult(
                skill_reference=reference.requirement,
                status=SkillChangeStatus.NO_CHANGES,
            )

        branch_name = self._dependencies.checkout.prepare_branch(entry, workspace)
        self._dependencies.skill_directory.copy_installed_skill(entry, workspace)
        self._dependencies.validator.validate(entry, workspace)
        self._dependencies.index_regenerator.regenerate_index(entry, workspace)
        prepared = self._dependencies.checkout.commit_changes(
            entry,
            workspace,
            branch_name,
        )
        return PublishSkillChangeResult(
            skill_reference=reference.requirement,
            status=SkillChangeStatus.CHANGED,
            prepared_contribution=prepared,
        )

    def _validate_required_provenance(
        self,
        entry: object,
        skill_reference: str,
    ) -> None:
        required_fields = (
            "source_revision",
            "index_digest",
            "target",
            "source",
            "source_type",
            "skill_path",
            "skill_file",
        )
        for field_name in required_fields:
            if not getattr(entry, field_name, None):
                raise IncompleteContributionProvenanceError(
                    skill_reference,
                    field_name,
                )
