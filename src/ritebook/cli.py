"""Ritebook command-line entry point and composition root."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.adapters.inbound.cli import run
from ritebook.features.linter.adapters.outbound.filesystem import (
    FilesystemSkillHeaderDiscovery,
)
from ritebook.features.linter.adapters.outbound.publisher_precheck import (
    LinterPublisherPrecheck,
)
from ritebook.features.linter.application.use_cases import (
    LintSkills,
    ValidateSkillHeaders,
)
from ritebook.features.publisher.adapters.outbound.filesystem import (
    FilesystemSkillDiscovery,
)
from ritebook.features.publisher.adapters.outbound.json_index import JsonIndexWriter
from ritebook.features.publisher.application.use_cases import PublishIndex

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
        precheck=LinterPublisherPrecheck(linter=linter),
        index_writer=JsonIndexWriter(),
        clock=lambda: datetime.now(UTC),
    )
    return run(argv, linter=linter, publisher=publisher)
