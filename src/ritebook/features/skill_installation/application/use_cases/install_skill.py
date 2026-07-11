"""Direct install-skill application use case."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.dtos import (
    InstallationManifestEntry,
    InstallSkillCommand,
    InstallSkillResult,
    SkillReference,
)
from ritebook.features.skill_installation.application.errors import (
    InvalidSkillReferenceError,
    UnknownInstallIndexError,
    UnknownInstallSkillError,
)
from ritebook.features.skill_installation.application.ports import InstallSkillPort

if TYPE_CHECKING:
    from collections.abc import Callable

    from ritebook.features.skill_installation.application.dtos import InstallableSkill
    from ritebook.features.skill_installation.application.ports import (
        InstallationManifestPort,
        SkillCatalogPort,
        SkillInstallerPort,
        SkillSourcePort,
    )


class InstallSkill(InstallSkillPort):
    """Install one cached skill into an explicit target path."""

    def __init__(
        self,
        *,
        catalog: SkillCatalogPort,
        source_resolver: SkillSourcePort,
        installer: SkillInstallerPort,
        manifest: InstallationManifestPort,
        clock: Callable[[], datetime],
    ) -> None:
        """Initialize direct installation orchestration dependencies."""
        self._catalog = catalog
        self._source_resolver = source_resolver
        self._installer = installer
        self._manifest = manifest
        self._clock = clock

    def execute(self, command: InstallSkillCommand) -> InstallSkillResult:
        """Resolve, install, and record one selected skill."""
        try:
            reference = SkillReference.parse(command.skill_reference)
        except ValueError as err:
            raise InvalidSkillReferenceError(str(err)) from err

        index = self._catalog.get_index(reference.index_name, command.registry_path)
        if index is None:
            raise UnknownInstallIndexError(reference.index_name)

        skill = self._find_skill(
            reference,
            self._catalog.read_skills(index.cached_index_path),
        )
        source = self._source_resolver.resolve_source(index)
        self._installer.install(
            source=source,
            skill=skill,
            target=command.target,
            force=command.force,
        )
        entry = InstallationManifestEntry(
            requirement=reference.requirement,
            index_name=reference.index_name,
            skill_name=reference.skill_name,
            target=command.target,
            source=source.source,
            source_type=source.source_type,
            source_revision=source.source_revision,
            index_schema_version=index.index_schema_version,
            skill_path=skill.path,
            skill_file=skill.skill_file,
            installed_at=_utc_timestamp(self._clock()),
        )
        self._manifest.write_installation(
            entry,
            command.installation_registry_path,
            force=command.force,
        )
        return InstallSkillResult(
            requirement=reference.requirement,
            target=command.target,
            manifest_entry=entry,
        )

    def _find_skill(
        self,
        reference: SkillReference,
        skills: tuple[InstallableSkill, ...],
    ) -> InstallableSkill:
        for skill in skills:
            if skill.name == reference.skill_name:
                return skill
        raise UnknownInstallSkillError(reference.requirement)


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Installation timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
