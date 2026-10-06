"""Lint-skills application use case."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, cast

from ritebook.features.skill_linter.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
    ParsedSkillHeader,
    ValidatedSkill,
)
from ritebook.features.skill_linter.application.ports import (
    LintSkillsPort,
    SkillHeaderDiscoveryPort,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ritebook.features.skill_linter.application.use_cases import (
        ValidateSkillHeaders,
    )


class LintSkills(LintSkillsPort):
    """Validate discovered skill headers without writing an index."""

    def __init__(
        self,
        *,
        header_discovery: SkillHeaderDiscoveryPort,
        header_validator: ValidateSkillHeaders,
    ) -> None:
        """Initialize the use case with header discovery and validation services."""
        self._header_discovery = header_discovery
        self._header_validator = header_validator

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
        """Discover, parse, and validate skill headers."""
        discovery_result = self._header_discovery.discover_headers(command.skills_root)
        validation_report = self._header_validator.execute(discovery_result.headers)
        issues = (*discovery_result.issues, *validation_report.issues)
        validated_skills = (
            tuple(_validated_skill(header) for header in discovery_result.headers)
            if not issues
            else ()
        )
        return LintSkillsResult.create(
            discovered_skill_count=discovery_result.discovered_skill_count,
            issues=issues,
            validated_skills=validated_skills,
        )


def _validated_skill(header: ParsedSkillHeader) -> ValidatedSkill:
    frontmatter = cast("Mapping[object, object]", header.frontmatter)
    name = cast("str", frontmatter["name"])
    description = cast("str", frontmatter["description"]).strip()
    return ValidatedSkill(
        path=PurePosixPath(header.skill_file).parent.as_posix(),
        name=name,
        skill_file=header.skill_file,
        description=description,
    )
