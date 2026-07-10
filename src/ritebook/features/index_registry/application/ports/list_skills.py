"""Inbound port for listing skills from registered cached indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import (
        ListSkillsCommand,
        ListSkillsResult,
    )


class ListSkillsPort(Protocol):
    """Application boundary for listing cached skills."""

    def execute(self, command: ListSkillsCommand) -> ListSkillsResult:
        """List skills from registered cached indexes."""
