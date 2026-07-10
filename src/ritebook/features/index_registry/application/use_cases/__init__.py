"""Application use cases for consumer index registration."""

from ritebook.features.index_registry.application.use_cases.add_index import AddIndex
from ritebook.features.index_registry.application.use_cases.list_indexes import (
    ListIndexes,
)
from ritebook.features.index_registry.application.use_cases.list_skills import (
    ListSkills,
)
from ritebook.features.index_registry.application.use_cases.update_index import (
    UpdateIndex,
)

__all__ = ["AddIndex", "ListIndexes", "ListSkills", "UpdateIndex"]
