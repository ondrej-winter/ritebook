"""Source repository adapter exports."""

from ritebook.features.skill_installation.adapters.outbound.source_repository import (
    adapter,
)

SourceRepositoryAdapter = adapter.SourceRepositoryAdapter

__all__ = ["SourceRepositoryAdapter"]
