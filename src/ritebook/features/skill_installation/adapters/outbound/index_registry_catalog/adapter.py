"""Bridge index-registry catalog data into skill-installation DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    RegisteredSkillIndex,
)

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.ports import (
        CachedIndexReaderPort,
        IndexRegistryPort,
    )


class IndexRegistrySkillCatalogAdapter:
    """Map index-registry read ports into the installation catalog port."""

    def __init__(
        self,
        *,
        registry: IndexRegistryPort,
        index_reader: CachedIndexReaderPort,
    ) -> None:
        """Initialize the bridge with index-registry-owned read dependencies."""
        self._registry = registry
        self._index_reader = index_reader

    def get_index(
        self,
        name: str,
        registry_path: str | None,
    ) -> RegisteredSkillIndex | None:
        """Return installation-owned registered index metadata."""
        entry = self._registry.get(name, registry_path)
        if entry is None:
            return None
        return RegisteredSkillIndex(
            name=entry.name,
            source=entry.source,
            source_type=entry.source_type.value,
            source_cache_path=entry.source_cache_path,
            cached_index_path=entry.cached_index_path,
            index_schema_version=entry.source_schema_version,
        )

    def read_skills(self, cached_index_path: str) -> tuple[InstallableSkill, ...]:
        """Return installation-owned skill metadata from a cached index."""
        return tuple(
            InstallableSkill(
                name=skill.name,
                path=skill.path,
                skill_file=skill.skill_file,
                source_root=skill.source_root,
            )
            for skill in self._index_reader.read_skills(cached_index_path)
        )
