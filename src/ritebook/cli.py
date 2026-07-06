"""Ritebook command-line entry point and composition root."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.features.skill_catalog.adapters.inbound.cli import run
from ritebook.features.skill_catalog.adapters.outbound.filesystem import (
    FilesystemSkillDiscovery,
    FilesystemSkillHeaderDiscovery,
)
from ritebook.features.skill_catalog.adapters.outbound.json_index import JsonIndexWriter
from ritebook.features.skill_catalog.application.use_cases import (
    LintSkills,
    PublishIndex,
    ValidateSkillHeaders,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Ritebook command-line interface."""
    linter = LintSkills(
        header_discovery=FilesystemSkillHeaderDiscovery(),
        header_validator=ValidateSkillHeaders(),
    )
    publisher = PublishIndex(
        skill_discovery=FilesystemSkillDiscovery(),
        header_discovery=FilesystemSkillHeaderDiscovery(),
        header_validator=ValidateSkillHeaders(),
        index_writer=JsonIndexWriter(),
        clock=lambda: datetime.now(UTC),
    )
    return run(argv, linter=linter, publisher=publisher)
