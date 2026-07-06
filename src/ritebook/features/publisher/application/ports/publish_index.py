"""Inbound port for publisher index generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.publisher.application.dtos import (
        PublishIndexCommand,
        PublishIndexResult,
    )


class PublishIndexPort(Protocol):
    """Application boundary for generating a publisher skill index."""

    def execute(self, command: PublishIndexCommand) -> PublishIndexResult:
        """Generate a skill index for the supplied command."""
