"""Lint-skills application use case."""

from ritebook.features.linter.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
)
from ritebook.features.linter.application.ports import (
    LintSkillsPort,
    SkillHeaderDiscoveryPort,
)
from ritebook.features.linter.application.use_cases import validate_skill_headers

ValidateSkillHeaders = validate_skill_headers.ValidateSkillHeaders


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
        return LintSkillsResult.create(
            validated_skill_count=len(discovery_result.headers),
            issues=(*discovery_result.issues, *validation_report.issues),
        )
