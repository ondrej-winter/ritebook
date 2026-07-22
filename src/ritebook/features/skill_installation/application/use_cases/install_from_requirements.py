"""Requirements-file install application use case."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.dtos import (
    InstallFromRequirementsCommand,
    InstallFromRequirementsResult,
    LockfileManifestEntry,
    PlannedInstallTarget,
    SkillReference,
)
from ritebook.features.skill_installation.application.errors import (
    DuplicateInstallTargetError,
    DuplicateSkillRequirementError,
    InvalidSkillReferenceError,
    PartialInstallationError,
    UndefinedInstallTargetError,
    UnknownInstallIndexError,
    UnknownInstallSkillError,
)
from ritebook.features.skill_installation.application.ports import (
    InstallFromRequirementsPort,
)

from ._provenance import repository_relative_source_path

if TYPE_CHECKING:
    from collections.abc import Callable

    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        RegisteredSkillIndex,
        ResolvedSkillSource,
        SkillRequirement,
    )
    from ritebook.features.skill_installation.application.ports import (
        InstallationManifestPort,
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
class _InstallPlanItem:
    reference: SkillReference
    target: str
    target_ref: str | None
    index: RegisteredSkillIndex
    skill: InstallableSkill
    source: ResolvedSkillSource
    planned_target: PlannedInstallTarget


class InstallFromRequirements(InstallFromRequirementsPort):
    """Install all skills declared by a parsed requirements file."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        requirements_reader: RequirementsReaderPort,
        catalog: SkillCatalogPort,
        source_resolver: SkillSourcePort,
        installer: SkillInstallerPort,
        manifest: InstallationManifestPort,
        clock: Callable[[], datetime],
    ) -> None:
        """Initialize requirements installation orchestration dependencies."""
        self._requirements_reader = requirements_reader
        self._catalog = catalog
        self._source_resolver = source_resolver
        self._installer = installer
        self._manifest = manifest
        self._clock = clock

    def execute(
        self,
        command: InstallFromRequirementsCommand,
    ) -> InstallFromRequirementsResult:
        """Plan, install, and lock all declared skill requirements."""
        requirements = self._requirements_reader.read_requirements(
            command.requirements_file,
        )
        with ExitStack() as source_stack:
            plan = self._plan_installations(
                command,
                requirements.skills,
                requirements.targets,
                source_stack,
            )

            copied_count = 0
            try:
                for item in plan:
                    self._installer.install(
                        source=item.source,
                        skill=item.skill,
                        target=item.target,
                        force=command.force,
                    )
                    copied_count += 1
            except Exception as err:
                if copied_count > 0:
                    raise PartialInstallationError from err
                raise

            entries = self._lockfile_entries(plan)
            self._manifest.write_lockfile(
                entries,
                command.lockfile_path,
                requirements_file=command.requirements_file,
            )
        return InstallFromRequirementsResult(
            requirements_file=command.requirements_file,
            installed_count=len(entries),
            lockfile_entries=entries,
        )

    def _plan_installations(
        self,
        command: InstallFromRequirementsCommand,
        requirements: tuple[SkillRequirement, ...],
        target_bases: dict[str, str],
        source_stack: ExitStack,
    ) -> tuple[_InstallPlanItem, ...]:
        resolved_requirements = self._resolve_requirements(
            requirements,
            target_bases,
            command.requirements_file,
        )
        sources: dict[str, ResolvedSkillSource] = {}
        plan = tuple(
            item
            for resolved_requirement in resolved_requirements
            for item in self._plan_items(
                command,
                resolved_requirement,
                source_stack,
                sources,
            )
        )
        self._reject_conflicting_targets(plan)
        return plan

    def _resolve_requirements(
        self,
        requirements: tuple[SkillRequirement, ...],
        target_bases: dict[str, str],
        requirements_file: str,
    ) -> tuple[_ResolvedRequirement, ...]:
        seen_requirements: set[str] = set()
        resolved: list[_ResolvedRequirement] = []

        for requirement in requirements:
            try:
                reference = SkillReference.parse(requirement.name)
            except ValueError as err:
                raise InvalidSkillReferenceError(str(err)) from err
            if reference.requirement in seen_requirements:
                raise DuplicateSkillRequirementError(reference.requirement)
            seen_requirements.add(reference.requirement)

            target_base = self._resolve_target_base(
                requirement,
                target_bases,
                requirements_file,
            )
            resolved.append(
                _ResolvedRequirement(
                    reference=reference,
                    target_base=target_base,
                    target_ref=requirement.target,
                    uses_target_path=requirement.target_path is not None,
                ),
            )

        return tuple(resolved)

    def _plan_items(
        self,
        command: InstallFromRequirementsCommand,
        resolved_requirement: _ResolvedRequirement,
        source_stack: ExitStack,
        sources: dict[str, ResolvedSkillSource],
    ) -> tuple[_InstallPlanItem, ...]:
        index = self._catalog.get_index(
            resolved_requirement.reference.index_name,
            command.registry_path,
        )
        if index is None:
            raise UnknownInstallIndexError(resolved_requirement.reference.index_name)

        source = sources.get(index.name)
        if source is None:
            source = source_stack.enter_context(
                self._source_resolver.open_source(index),
            )
            sources[index.name] = source
        skills = self._find_skills(
            resolved_requirement.reference,
            self._catalog.read_skills(index.cached_index_path),
        )
        items: list[_InstallPlanItem] = []
        for skill in skills:
            target = self._target_for_skill(resolved_requirement, skill)
            items.append(
                _InstallPlanItem(
                    reference=_reference_for_skill(resolved_requirement, skill),
                    target=target,
                    target_ref=resolved_requirement.target_ref,
                    index=index,
                    skill=skill,
                    source=source,
                    planned_target=self._installer.plan_target(target),
                ),
            )
        return tuple(items)

    def _resolve_target_base(
        self,
        requirement: SkillRequirement,
        target_bases: dict[str, str],
        requirements_file: str,
    ) -> str:
        if requirement.target_path is not None:
            return requirement.target_path
        if requirement.target is None:
            msg = "Skill entries must define exactly one of target or target_path."
            raise InvalidSkillReferenceError(msg)
        target_base = target_bases.get(requirement.target)
        if target_base is None:
            raise UndefinedInstallTargetError(requirement.target, requirements_file)
        return target_base

    def _target_for_skill(
        self,
        resolved_requirement: _ResolvedRequirement,
        skill: InstallableSkill,
    ) -> str:
        if resolved_requirement.uses_target_path and (
            skill.path == resolved_requirement.reference.skill_path
        ):
            return resolved_requirement.target_base
        return str(PurePath(resolved_requirement.target_base, skill.name))

    def _find_skills(
        self,
        reference: SkillReference,
        skills: tuple[InstallableSkill, ...],
    ) -> tuple[InstallableSkill, ...]:
        for skill in skills:
            if skill.path == reference.skill_path:
                return (skill,)
        matching_prefix = tuple(
            sorted(
                (
                    skill
                    for skill in skills
                    if skill.path.startswith(f"{reference.skill_path}/")
                ),
                key=lambda skill: skill.path,
            ),
        )
        if matching_prefix:
            return matching_prefix
        raise UnknownInstallSkillError(reference.requirement)

    def _reject_conflicting_targets(self, plan: tuple[_InstallPlanItem, ...]) -> None:
        seen_targets: list[_InstallPlanItem] = []
        for item in plan:
            if any(_targets_overlap(item, seen) for seen in seen_targets):
                raise DuplicateInstallTargetError(item.target)
            seen_targets.append(item)

    def _lockfile_entries(
        self,
        plan: tuple[_InstallPlanItem, ...],
    ) -> tuple[LockfileManifestEntry, ...]:
        locked_at = _utc_timestamp(self._clock())
        return tuple(
            LockfileManifestEntry(
                requirement=item.reference.requirement,
                index_name=item.reference.index_name,
                skill_name=item.reference.skill_name,
                target=item.target,
                source=item.source.source,
                source_type=item.source.source_type,
                source_revision=item.source.source_revision,
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
                target_ref=item.target_ref,
                locked_at=locked_at,
            )
            for item in sorted(
                plan,
                key=lambda plan_item: (
                    plan_item.reference.index_name,
                    plan_item.reference.skill_path,
                ),
            )
        )


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Installation timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _reference_for_skill(
    resolved_requirement: _ResolvedRequirement,
    skill: InstallableSkill,
) -> SkillReference:
    if skill.path == resolved_requirement.reference.skill_path:
        return resolved_requirement.reference
    return SkillReference.parse(
        f"{resolved_requirement.reference.index_name}/{skill.path}",
    )


def _targets_overlap(first: _InstallPlanItem, second: _InstallPlanItem) -> bool:
    first_parts = PurePath(first.planned_target.canonical_target).parts
    second_parts = PurePath(second.planned_target.canonical_target).parts
    shared_length = min(len(first_parts), len(second_parts))
    return first_parts[:shared_length] == second_parts[:shared_length]
