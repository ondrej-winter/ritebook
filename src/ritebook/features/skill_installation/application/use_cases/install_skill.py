"""Ownership-aware direct install application use case."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.dtos import (
    InstallationStatus,
    InstallationWorkflow,
    InstallSkillResult,
    OwnedInstallation,
    SkillReference,
)
from ritebook.features.skill_installation.application.errors import (
    CommittedSkillMetadataMismatchError,
    ExistingInstallTargetError,
    InvalidSkillReferenceError,
    LocallyModifiedInstallTargetError,
    UnknownInstallIndexError,
    UnknownInstallSkillError,
    UnmanagedInstallTargetError,
)
from ritebook.features.skill_installation.application.ports import InstallSkillPort

from ._provenance import repository_relative_source_path

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        CommittedSkillHeader,
        InstallableSkill,
        InstallSkillCommand,
        PlannedInstallTarget,
        ResolvedSkillSource,
        StagedSkillTree,
    )
    from ritebook.features.skill_installation.application.ports import (
        CommittedSkillValidatorPort,
        InstallationStatePort,
        InstallationTransactionPort,
        SkillCatalogPort,
        SkillInstallerPort,
        SkillSourcePort,
    )


class InstallSkill(InstallSkillPort):
    """Install one exact skill while preserving ownership and local edits."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        catalog: SkillCatalogPort,
        source_resolver: SkillSourcePort,
        committed_skill_validator: CommittedSkillValidatorPort,
        installer: SkillInstallerPort,
        state: InstallationStatePort,
        transactions: InstallationTransactionPort,
    ) -> None:
        """Initialize direct-install orchestration dependencies."""
        self._catalog = catalog
        self._source_resolver = source_resolver
        self._committed_skill_validator = committed_skill_validator
        self._installer = installer
        self._state = state
        self._transactions = transactions

    def execute(self, command: InstallSkillCommand) -> InstallSkillResult:
        """Verify, stage, place, and record one exact selected skill."""
        try:
            reference = SkillReference.parse(command.skill_reference)
        except ValueError as err:
            raise InvalidSkillReferenceError(str(err)) from err

        paths = self._state.direct_paths(command.installation_registry_path)
        with self._transactions.open(
            lock_path=paths.lock_path,
            journal_path=paths.journal_path,
        ) as transaction:
            ownership_snapshot = self._state.read_ownership(paths.ownership_path)
            ownership = ownership_snapshot.entries
            index = self._catalog.get_index(reference.index_name, command.registry_path)
            if index is None:
                raise UnknownInstallIndexError(reference.index_name)

            with self._source_resolver.open_source(index) as source:
                skill = _find_skill(
                    reference,
                    self._catalog.read_skills(
                        index.cached_index_path,
                        index.index_digest,
                    ),
                )
                _validate_committed_metadata(
                    skill,
                    self._committed_skill_validator.validate(source, skill),
                )
                planned_target = self._installer.plan_target(command.target)
                inspection = self._installer.inspect_target(planned_target)
                owner = _owner_for_target(ownership, planned_target.canonical_target)
                expected_digest = _replacement_digest(
                    target=command.target,
                    exists=inspection.exists,
                    current_digest=inspection.installed_tree_digest,
                    owner=owner,
                    force=command.force,
                )
                staged = self._installer.stage(
                    source=source,
                    skill=skill,
                    target=planned_target,
                )
                try:
                    transaction.replace_tree(
                        staged_path=staged.staged_path,
                        target_path=planned_target.canonical_target,
                        expected_digest=expected_digest,
                    )
                    entry = _owned_entry(
                        reference=reference,
                        target=planned_target,
                        source=source,
                        skill=skill,
                        staged=staged,
                    )
                    updated = tuple(
                        sorted(
                            (
                                entry,
                                *(
                                    existing
                                    for existing in ownership
                                    if existing.canonical_target
                                    != planned_target.canonical_target
                                ),
                            ),
                            key=lambda item: item.target_id,
                        ),
                    )
                    state_file = self._state.ownership_file(
                        updated,
                        paths.ownership_path,
                        expected_digest=ownership_snapshot.digest,
                    )
                    transaction.commit_state((state_file,))
                finally:
                    self._installer.cleanup_staged(staged)

        return InstallSkillResult(
            requirement=reference.requirement,
            target=command.target,
            ownership_entry=entry,
        )


def _find_skill(
    reference: SkillReference,
    skills: tuple[InstallableSkill, ...],
) -> InstallableSkill:
    for skill in skills:
        if skill.path == reference.skill_path:
            return skill
    raise UnknownInstallSkillError(reference.requirement)


def _validate_committed_metadata(
    skill: InstallableSkill,
    committed_header: CommittedSkillHeader,
) -> None:
    if (
        committed_header.name != skill.name
        or committed_header.description != skill.description
    ):
        raise CommittedSkillMetadataMismatchError(skill.path)


def _owner_for_target(
    entries: tuple[OwnedInstallation, ...],
    canonical_target: str,
) -> OwnedInstallation | None:
    for entry in entries:
        if entry.canonical_target == canonical_target:
            return entry
    return None


def _replacement_digest(
    *,
    target: str,
    exists: bool,
    current_digest: str | None,
    owner: OwnedInstallation | None,
    force: bool,
) -> str | None:
    if not exists:
        return None
    if owner is None:
        raise UnmanagedInstallTargetError(target)
    if current_digest != owner.installed_tree_digest:
        raise LocallyModifiedInstallTargetError(target)
    if not force:
        raise ExistingInstallTargetError(target)
    return owner.installed_tree_digest


def _owned_entry(
    *,
    reference: SkillReference,
    target: PlannedInstallTarget,
    source: ResolvedSkillSource,
    skill: InstallableSkill,
    staged: StagedSkillTree,
) -> OwnedInstallation:
    return OwnedInstallation(
        workflow=InstallationWorkflow.DIRECT,
        requirement=reference.requirement,
        index_name=reference.index_name,
        skill_name=reference.skill_name,
        target=target.requested_target,
        target_id=_target_id(target.canonical_target),
        canonical_target=target.canonical_target,
        source=source.source,
        source_type=source.source_type,
        source_revision=source.source_revision,
        source_branch=source.source_branch,
        index_digest=source.index_digest,
        index_schema_version=1,
        skill_path=repository_relative_source_path(skill.source_root, skill.path),
        skill_file=repository_relative_source_path(
            skill.source_root,
            skill.skill_file,
        ),
        installed_tree_digest=staged.installed_tree_digest,
        status=InstallationStatus.MATERIALIZED,
    )


def _target_id(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"
