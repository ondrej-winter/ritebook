"""List-skills application use case."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import (
    CachedSkillSummary,
    ListedIndexSkills,
    ListSkillsCommand,
    ListSkillsResult,
    RegisteredIndex,
)
from ritebook.features.index_registry.application.errors import UnknownIndexNameError
from ritebook.features.index_registry.application.ports import ListSkillsPort

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.ports import (
        CachedIndexReaderPort,
        IndexRegistryPort,
    )


class ListSkills(ListSkillsPort):
    """List skills from registered cached indexes."""

    def __init__(
        self,
        *,
        registry: IndexRegistryPort,
        cached_index_reader: CachedIndexReaderPort,
    ) -> None:
        """Initialize list-skills dependencies."""
        self._registry = registry
        self._cached_index_reader = cached_index_reader

    def execute(self, command: ListSkillsCommand) -> ListSkillsResult:
        """Return cached skills grouped by effective index name."""
        entries = self._selected_entries(command)
        return ListSkillsResult(
            indexes=tuple(self._listed_index(entry) for entry in entries),
        )

    def _selected_entries(
        self,
        command: ListSkillsCommand,
    ) -> tuple[RegisteredIndex, ...]:
        if command.index_name is not None:
            entry = self._registry.get(command.index_name, command.registry_path)
            if entry is None:
                raise UnknownIndexNameError(command.index_name)
            return (entry,)
        return tuple(
            sorted(
                self._registry.list(command.registry_path),
                key=lambda entry: entry.name,
            ),
        )

    def _listed_index(self, entry: RegisteredIndex) -> ListedIndexSkills:
        return ListedIndexSkills(
            index_name=entry.name,
            skills=_sorted_skills(
                self._cached_index_reader.read_skills(entry.cached_index_path),
            ),
        )


def _sorted_skills(
    skills: tuple[CachedSkillSummary, ...],
) -> tuple[CachedSkillSummary, ...]:
    return tuple(sorted(skills, key=lambda skill: skill.path))
