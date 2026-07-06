"""Publish-index application use case."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from ritebook.features.publisher.application.dtos import (
    CANONICAL_INDEX_FILENAME,
    PublishIndexCommand,
    PublishIndexResult,
    PublishIndexValidationError,
)
from ritebook.features.publisher.application.ports import (
    PublishIndexPort,
    SkillDiscoveryPort,
    SkillIndexWriterPort,
    SkillPrecheckPort,
)
from ritebook.features.publisher.domain import SkillCatalog


class PublishIndex(PublishIndexPort):
    """Generate and write a publisher skill index through application ports."""

    def __init__(
        self,
        *,
        skill_discovery: SkillDiscoveryPort,
        precheck: SkillPrecheckPort,
        index_writer: SkillIndexWriterPort,
        clock: Callable[[], datetime],
    ) -> None:
        """Initialize the use case with outbound ports and a timestamp source."""
        self._skill_discovery = skill_discovery
        self._precheck = precheck
        self._index_writer = index_writer
        self._clock = clock

    def execute(self, command: PublishIndexCommand) -> PublishIndexResult:
        """Discover skills, write their catalog, and return publish details."""
        precheck_result = self._precheck.run_prechecks(command.skills_root)
        if not precheck_result.succeeded:
            raise PublishIndexValidationError(precheck_result.issues)

        skills = self._skill_discovery.discover_skills(command.skills_root)
        catalog = SkillCatalog.create(
            generated_at=_utc_timestamp(self._clock()),
            skills_root=command.skills_root,
            skills=skills,
        )
        self._index_writer.write_index(catalog, CANONICAL_INDEX_FILENAME)
        return PublishIndexResult(
            discovered_skill_count=len(skills),
            output_path=CANONICAL_INDEX_FILENAME,
        )


def _utc_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Publish index timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC)
