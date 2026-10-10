"""Ownership-aware exact reconciliation from a requirements file."""

from __future__ import annotations

import hashlib
from contextlib import ExitStack
from dataclasses import dataclass, replace
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.dtos import (
    InstallationStatus,
    InstallationWorkflow,
    InstallFromRequirementsResult,
    OwnedInstallation,
    ReconciliationIssue,
    SkillReference,
)
from ritebook.features.skill_installation.application.errors import (
    CommittedSkillMetadataMismatchError,
    DuplicateInstallTargetError,
    DuplicateSkillRequirementError,
    InvalidSkillReferenceError,
    UndefinedInstallTargetError,
    UnknownInstallIndexError,
    UnknownInstallSkillError,
)
from ritebook.features.skill_installation.application.ports import (
    InstallFromRequirementsPort,
)
from ritebook.shared_kernel.catalog_paths import (
    CatalogPathKind,
    validate_catalog_path,
)

from ._provenance import repository_relative_source_path

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        InstallFromRequirementsCommand,
        PlannedInstallTarget,
        RegisteredSkillIndex,
        ResolvedSkillSource,
        SkillRequirement,
        StagedSkillTree,
    )
    from ritebook.features.skill_installation.application.ports import (
        CommittedSkillValidatorPort,
        IndexRefresherPort,
        InstallationStatePort,
        InstallationTransaction,
        InstallationTransactionPort,
        RequirementsReaderPort,
        SkillCatalogPort,
        SkillInstallerPort,
        SkillSourcePort,
    )


@dataclass(frozen=True)
class _ResolvedRequirement:
    reference: SkillReference
    target_base: str
    target_ref: str | None
    uses_target_path: bool


@dataclass(frozen=True)
class _SelectedInstall:
    reference: SkillReference
    portable_target: str
    target_ref: str | None
    index: RegisteredSkillIndex
    skill: InstallableSkill
    source: ResolvedSkillSource


@dataclass(frozen=True)
class _DesiredInstall:
    reference: SkillReference
    portable_target: str
    target_ref: str | None
    index: RegisteredSkillIndex
    skill: InstallableSkill
    source: ResolvedSkillSource
    planned_target: PlannedInstallTarget


@dataclass(frozen=True)
class _ReconciliationOutcome:
    entries: tuple[OwnedInstallation, ...] = ()
    issues: tuple[ReconciliationIssue, ...] = ()
    installed_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    pruned_count: int = 0


class InstallFromRequirements(InstallFromRequirementsPort):
    """Refresh and exactly reconcile declared repository skill installations."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        requirements_reader: RequirementsReaderPort,
        index_refresher: IndexRefresherPort,
        catalog: SkillCatalogPort,
        source_resolver: SkillSourcePort,
        committed_skill_validator: CommittedSkillValidatorPort,
        installer: SkillInstallerPort,
        state: InstallationStatePort,
        transactions: InstallationTransactionPort,
    ) -> None:
        """Initialize reconciliation orchestration dependencies."""
        self._requirements_reader = requirements_reader
        self._index_refresher = index_refresher
        self._catalog = catalog
        self._source_resolver = source_resolver
        self._committed_skill_validator = committed_skill_validator
        self._installer = installer
        self._state = state
        self._transactions = transactions

    def execute(
        self,
        command: InstallFromRequirementsCommand,
    ) -> InstallFromRequirementsResult:
        """Refresh indexes and reconcile owned targets with desired requirements."""
        requirements = self._requirements_reader.read_requirements(
            command.requirements_file,
        )
        paths = self._state.sync_paths(
            requirements_file=command.requirements_file,
            lockfile_path=command.lockfile_path,
        )
        if paths.lockfile_path is None:
            msg = "Sync operation paths must include a lockfile path."
            raise ValueError(msg)

        staged_trees: list[StagedSkillTree] = []

        try:
            with self._transactions.open(
                lock_path=paths.lock_path,
                journal_path=paths.journal_path,
            ) as transaction:
                if self._state.ownership_exists(paths.ownership_path):
                    ownership_snapshot = self._state.read_ownership(
                        paths.ownership_path,
                    )
                    ownership = ownership_snapshot.entries
                    ownership_digest = ownership_snapshot.digest
                    lockfile_digest = self._state.read_state_digest(paths.lockfile_path)
                else:
                    lockfile_snapshot = self._state.read_lockfile_ownership(
                        paths.lockfile_path,
                        requirements_file=command.requirements_file,
                    )
                    ownership = lockfile_snapshot.entries
                    ownership_digest = None
                    lockfile_digest = lockfile_snapshot.digest
                aliases = _referenced_aliases(requirements.skills)
                for alias in aliases:
                    self._index_refresher.refresh(alias, command.registry_path)

                with ExitStack() as source_stack:
                    desired = self._desired_installations(
                        command,
                        requirements.skills,
                        requirements.targets,
                        source_stack,
                    )
                    _reject_conflicting_targets(desired)
                    ownership_by_target = {entry.canonical_target: entry for entry in ownership}
                    desired_outcome = self._reconcile_desired(
                        desired,
                        ownership_by_target,
                        transaction,
                        force=command.force,
                        staged_trees=staged_trees,
                    )
                    obsolete_outcome = self._reconcile_obsolete(
                        ownership,
                        desired,
                        transaction,
                    )

                    final_entries = tuple(
                        sorted(
                            (*desired_outcome.entries, *obsolete_outcome.entries),
                            key=lambda entry: entry.target_id,
                        ),
                    )
                    final_issues = tuple(
                        sorted(
                            (*desired_outcome.issues, *obsolete_outcome.issues),
                            key=lambda issue: (
                                issue.target,
                                issue.code,
                                issue.requirement or "",
                            ),
                        ),
                    )
                    ownership_file = self._state.ownership_file(
                        final_entries,
                        paths.ownership_path,
                        expected_digest=ownership_digest,
                    )
                    lockfile = self._state.lockfile(
                        final_entries,
                        final_issues,
                        paths.lockfile_path,
                        requirements_file=_portable_requirements_file(
                            command.requirements_file,
                        ),
                        expected_digest=lockfile_digest,
                    )
                    transaction.commit_state((ownership_file, lockfile))
        finally:
            for staged in staged_trees:
                self._installer.cleanup_staged(staged)

        return InstallFromRequirementsResult(
            requirements_file=command.requirements_file,
            installed_count=desired_outcome.installed_count,
            updated_count=desired_outcome.updated_count,
            unchanged_count=desired_outcome.unchanged_count,
            pruned_count=obsolete_outcome.pruned_count,
            ownership_entries=final_entries,
            issues=final_issues,
        )

    def _reconcile_desired(
        self,
        desired: tuple[_DesiredInstall, ...],
        ownership_by_target: dict[str, OwnedInstallation],
        transaction: InstallationTransaction,
        *,
        force: bool,
        staged_trees: list[StagedSkillTree],
    ) -> _ReconciliationOutcome:
        entries: list[OwnedInstallation] = []
        issues: list[ReconciliationIssue] = []
        installed_count = 0
        updated_count = 0
        unchanged_count = 0

        for item in desired:
            owner = ownership_by_target.get(item.planned_target.canonical_target)
            inspection = self._installer.inspect_target(item.planned_target)
            if inspection.exists and owner is None:
                issues.append(
                    _issue(
                        "unmanaged-target",
                        item,
                        "target exists but is not owned by Ritebook",
                    ),
                )
                continue
            if (
                inspection.exists
                and owner is not None
                and inspection.installed_tree_digest != owner.installed_tree_digest
            ):
                entries.append(
                    replace(
                        owner,
                        desired=True,
                        status=InstallationStatus.LOCAL_CHANGES,
                    ),
                )
                issues.append(
                    _issue(
                        "local-changes",
                        item,
                        "target has local changes and was preserved",
                    ),
                )
                continue

            staged = self._installer.stage(
                source=item.source,
                skill=item.skill,
                target=item.planned_target,
            )
            staged_trees.append(staged)
            candidate = _owned_entry(item, staged)
            if (
                inspection.exists
                and owner is not None
                and staged.installed_tree_digest == owner.installed_tree_digest
                and not force
            ):
                entries.append(candidate)
                unchanged_count += 1
                continue

            transaction.replace_tree(
                staged_path=staged.staged_path,
                target_path=item.planned_target.canonical_target,
                expected_digest=(owner.installed_tree_digest if inspection.exists and owner is not None else None),
            )
            entries.append(candidate)
            if inspection.exists:
                updated_count += 1
            else:
                installed_count += 1

        return _ReconciliationOutcome(
            entries=tuple(entries),
            issues=tuple(issues),
            installed_count=installed_count,
            updated_count=updated_count,
            unchanged_count=unchanged_count,
        )

    def _reconcile_obsolete(
        self,
        ownership: tuple[OwnedInstallation, ...],
        desired: tuple[_DesiredInstall, ...],
        transaction: InstallationTransaction,
    ) -> _ReconciliationOutcome:
        desired_targets = {item.planned_target.canonical_target for item in desired}
        entries: list[OwnedInstallation] = []
        issues: list[ReconciliationIssue] = []
        pruned_count = 0

        for owner in ownership:
            if owner.canonical_target in desired_targets:
                continue
            planned = self._installer.plan_target(owner.canonical_target)
            inspection = self._installer.inspect_target(planned)
            if inspection.exists and inspection.installed_tree_digest == owner.installed_tree_digest:
                transaction.remove_tree(
                    target_path=owner.canonical_target,
                    expected_digest=owner.installed_tree_digest,
                )
                pruned_count += 1
                continue
            status = InstallationStatus.LOCAL_CHANGES if inspection.exists else InstallationStatus.RETAINED
            entries.append(replace(owner, desired=False, status=status))
            issues.append(_obsolete_issue(owner, exists=inspection.exists))

        return _ReconciliationOutcome(
            entries=tuple(entries),
            issues=tuple(issues),
            pruned_count=pruned_count,
        )

    def _desired_installations(
        self,
        command: InstallFromRequirementsCommand,
        requirements: tuple[SkillRequirement, ...],
        target_bases: dict[str, str],
        source_stack: ExitStack,
    ) -> tuple[_DesiredInstall, ...]:
        root = Path(command.requirements_file).expanduser().resolve(strict=False).parent
        seen_requirements: set[str] = set()
        sources: dict[str, ResolvedSkillSource] = {}
        selected: list[_SelectedInstall] = []

        for requirement in requirements:
            if requirement.name in seen_requirements:
                raise DuplicateSkillRequirementError(requirement.name)
            seen_requirements.add(requirement.name)
            try:
                reference = SkillReference.parse(requirement.name)
            except ValueError as err:
                raise InvalidSkillReferenceError(str(err)) from err
            resolved = _resolve_requirement(
                reference,
                requirement,
                target_bases,
                command.requirements_file,
            )
            index = self._catalog.get_index(reference.index_name, command.registry_path)
            if index is None:
                raise UnknownInstallIndexError(reference.index_name)
            source = sources.get(index.name)
            if source is None:
                source = source_stack.enter_context(
                    self._source_resolver.open_source(index),
                )
                sources[index.name] = source
            skills, expands_collection = _find_skills(
                reference,
                self._catalog.read_skills(
                    index.cached_index_path,
                    index.index_digest,
                ),
            )
            if resolved.uses_target_path and expands_collection:
                msg = "A collection selector must use target, not target_path."
                raise InvalidSkillReferenceError(msg)
            for skill in skills:
                exact_reference = _reference_for_skill(resolved, skill)
                portable_target = _portable_target(resolved, exact_reference)
                committed_header = self._committed_skill_validator.validate(
                    source,
                    skill,
                )
                if committed_header.name != skill.name or committed_header.description != skill.description:
                    raise CommittedSkillMetadataMismatchError(skill.path)
                selected.append(
                    _SelectedInstall(
                        reference=exact_reference,
                        portable_target=portable_target,
                        target_ref=resolved.target_ref,
                        index=index,
                        skill=skill,
                        source=source,
                    ),
                )
        return tuple(
            _DesiredInstall(
                reference=item.reference,
                portable_target=item.portable_target,
                target_ref=item.target_ref,
                index=item.index,
                skill=item.skill,
                source=item.source,
                planned_target=self._installer.plan_target(
                    str(root / item.portable_target),
                ),
            )
            for item in selected
        )


def _referenced_aliases(
    requirements: tuple[SkillRequirement, ...],
) -> tuple[str, ...]:
    try:
        return tuple(
            sorted({SkillReference.parse(requirement.name).index_name for requirement in requirements}),
        )
    except ValueError as err:
        raise InvalidSkillReferenceError(str(err)) from err


def _resolve_requirement(
    reference: SkillReference,
    requirement: SkillRequirement,
    target_bases: dict[str, str],
    requirements_file: str,
) -> _ResolvedRequirement:
    if requirement.target_path is not None:
        target_base = requirement.target_path
        target_ref = None
        uses_target_path = True
    else:
        if requirement.target is None:
            msg = "Skill entries must define exactly one of target or target_path."
            raise InvalidSkillReferenceError(msg)
        target_base = target_bases.get(requirement.target)
        if target_base is None:
            raise UndefinedInstallTargetError(requirement.target, requirements_file)
        target_ref = requirement.target
        uses_target_path = False
    return _ResolvedRequirement(
        reference=reference,
        target_base=target_base,
        target_ref=target_ref,
        uses_target_path=uses_target_path,
    )


def _portable_target(
    resolved: _ResolvedRequirement,
    reference: SkillReference,
) -> str:
    if resolved.uses_target_path and reference == resolved.reference:
        value = resolved.target_base
    else:
        value = str(PurePath(resolved.target_base, reference.skill_name))
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        msg = f"sync target must be a portable relative path: {value}"
        raise InvalidSkillReferenceError(msg)
    normalized = PurePath(value).as_posix()
    if normalized in {"", "."}:
        msg = f"sync target must be a portable relative path: {value}"
        raise InvalidSkillReferenceError(msg)
    return normalized


def _find_skills(
    reference: SkillReference,
    skills: tuple[InstallableSkill, ...],
) -> tuple[tuple[InstallableSkill, ...], bool]:
    for skill in skills:
        if skill.path == reference.skill_path:
            return (skill,), False
    selector = validate_catalog_path(reference.skill_path)
    if selector.kind is not CatalogPathKind.ROOT_SKILL:
        raise UnknownInstallSkillError(reference.requirement)
    children = tuple(
        sorted(
            (skill for skill in skills if _is_immediate_collection_child(skill.path, selector.value)),
            key=lambda skill: skill.path,
        ),
    )
    if children:
        return children, True
    raise UnknownInstallSkillError(reference.requirement)


def _reference_for_skill(
    resolved: _ResolvedRequirement,
    skill: InstallableSkill,
) -> SkillReference:
    if skill.path == resolved.reference.skill_path:
        return resolved.reference
    return SkillReference.parse(f"{resolved.reference.index_name}/{skill.path}")


def _is_immediate_collection_child(path: str, collection: str) -> bool:
    catalog_path = validate_catalog_path(path)
    return catalog_path.kind is CatalogPathKind.COLLECTION_CHILD and catalog_path.collection == collection


def _reject_conflicting_targets(desired: tuple[_DesiredInstall, ...]) -> None:
    seen: list[_DesiredInstall] = []
    for item in desired:
        if any(_targets_overlap(item, other) for other in seen):
            raise DuplicateInstallTargetError(item.portable_target)
        seen.append(item)


def _targets_overlap(first: _DesiredInstall, second: _DesiredInstall) -> bool:
    first_parts = PurePath(first.planned_target.canonical_target).parts
    second_parts = PurePath(second.planned_target.canonical_target).parts
    shared_length = min(len(first_parts), len(second_parts))
    return first_parts[:shared_length] == second_parts[:shared_length]


def _owned_entry(
    item: _DesiredInstall,
    staged: StagedSkillTree,
) -> OwnedInstallation:
    return OwnedInstallation(
        workflow=InstallationWorkflow.SYNC,
        requirement=item.reference.requirement,
        index_name=item.reference.index_name,
        skill_name=item.reference.skill_name,
        target=item.portable_target,
        target_id=_target_id(item.portable_target),
        canonical_target=item.planned_target.canonical_target,
        source=item.source.source,
        source_type=item.source.source_type,
        source_revision=item.source.source_revision,
        source_branch=item.source.source_branch,
        index_digest=item.source.index_digest,
        index_schema_version=item.index.index_schema_version,
        skill_path=repository_relative_source_path(
            item.skill.source_root,
            item.skill.path,
        ),
        skill_file=repository_relative_source_path(
            item.skill.source_root,
            item.skill.skill_file,
        ),
        installed_tree_digest=staged.installed_tree_digest,
        target_ref=item.target_ref,
    )


def _issue(code: str, item: _DesiredInstall, detail: str) -> ReconciliationIssue:
    return ReconciliationIssue(
        code=code,
        target=item.portable_target,
        requirement=item.reference.requirement,
        detail=detail,
    )


def _obsolete_issue(
    owner: OwnedInstallation,
    *,
    exists: bool,
) -> ReconciliationIssue:
    return ReconciliationIssue(
        code="local-changes" if exists else "missing-owned-target",
        target=owner.target,
        requirement=owner.requirement,
        detail=(
            "target has local changes and was preserved"
            if exists
            else "owned target is missing and requires inspection"
        ),
    )


def _target_id(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _portable_requirements_file(value: str) -> str:
    path = Path(value).expanduser()
    return path.name if path.is_absolute() else PurePath(value).as_posix()
