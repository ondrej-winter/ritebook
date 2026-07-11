"""Requirements-file install application use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.dtos import (
    InstallFromRequirementsCommand,
    InstallFromRequirementsResult,
    LockfileManifestEntry,
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
    target: str
    target_ref: str | None


@dataclass(frozen=True)
class _InstallPlanItem:
    reference: SkillReference
    target: str
    target_ref: str | None
    index: RegisteredSkillIndex
    skill: InstallableSkill
    source: ResolvedSkillSource


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
        plan = self._plan_installations(
            command,
            requirements.skills,
            requirements.targets,
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
    ) -> tuple[_InstallPlanItem, ...]:
        resolved_requirements = self._resolve_requirements(
            requirements,
            target_bases,
            command.requirements_file,
        )
        return tuple(
            self._plan_item(command, resolved_requirement)
            for resolved_requirement in resolved_requirements
        )

    def _resolve_requirements(
        self,
        requirements: tuple[SkillRequirement, ...],
        target_bases: dict[str, str],
        requirements_file: str,
    ) -> tuple[_ResolvedRequirement, ...]:
        seen_requirements: set[str] = set()
        seen_targets: set[str] = set()
        resolved: list[_ResolvedRequirement] = []

        for requirement in requirements:
            try:
                reference = SkillReference.parse(requirement.name)
            except ValueError as err:
                raise InvalidSkillReferenceError(str(err)) from err
            if reference.requirement in seen_requirements:
                raise DuplicateSkillRequirementError(reference.requirement)
            seen_requirements.add(reference.requirement)

            target = self._resolve_target(
                requirement,
                reference,
                target_bases,
                requirements_file,
            )
            if target in seen_targets:
                raise DuplicateInstallTargetError(target)
            seen_targets.add(target)
            resolved.append(
                _ResolvedRequirement(
                    reference=reference,
                    target=target,
                    target_ref=requirement.target,
                ),
            )

        return tuple(resolved)

    def _plan_item(
        self,
        command: InstallFromRequirementsCommand,
        resolved_requirement: _ResolvedRequirement,
    ) -> _InstallPlanItem:
        index = self._catalog.get_index(
            resolved_requirement.reference.index_name,
            command.registry_path,
        )
        if index is None:
            raise UnknownInstallIndexError(resolved_requirement.reference.index_name)

        skill = self._find_skill(
            resolved_requirement.reference,
            self._catalog.read_skills(index.cached_index_path),
        )
        source = self._source_resolver.resolve_source(index)
        return _InstallPlanItem(
            reference=resolved_requirement.reference,
            target=resolved_requirement.target,
            target_ref=resolved_requirement.target_ref,
            index=index,
            skill=skill,
            source=source,
        )

    def _resolve_target(
        self,
        requirement: SkillRequirement,
        reference: SkillReference,
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
        return str(PurePath(target_base, reference.skill_name))

    def _find_skill(
        self,
        reference: SkillReference,
        skills: tuple[InstallableSkill, ...],
    ) -> InstallableSkill:
        for skill in skills:
            if skill.name == reference.skill_name:
                return skill
        raise UnknownInstallSkillError(reference.requirement)

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
                index_schema_version=item.index.index_schema_version,
                skill_path=item.skill.path,
                skill_file=item.skill.skill_file,
                target_ref=item.target_ref,
                locked_at=locked_at,
            )
            for item in sorted(
                plan,
                key=lambda plan_item: (
                    plan_item.reference.index_name,
                    plan_item.reference.skill_name,
                ),
            )
        )


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Installation timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
