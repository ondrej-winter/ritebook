"""Filesystem implementation of skill discovery."""

from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    FilesystemSkillDiscoveryError,
    discover_skill_files,
)
from ritebook.features.linter.adapters.outbound.filesystem.frontmatter import (
    parse_skill_header,
)
from ritebook.features.linter.application.dtos import (
    ParsedSkillHeader,
    SkillHeaderDiscoveryResult,
    SkillValidationIssue,
)
from ritebook.features.linter.application.errors import LintSkillsDiscoveryError


class FilesystemSkillHeaderDiscovery:
    """Discover and parse skill headers from ``SKILL.md`` files."""

    def discover_headers(self, skills_root: str) -> SkillHeaderDiscoveryResult:
        """Discover non-hidden skill headers below the explicit skills root."""
        headers: list[ParsedSkillHeader] = []
        issues: list[SkillValidationIssue] = []
        try:
            discovered_files = discover_skill_files(Path(skills_root))
        except FilesystemSkillDiscoveryError as err:
            raise LintSkillsDiscoveryError(str(err)) from err

        for discovered in discovered_files:
            parsed = parse_skill_header(
                discovered.path,
                relative_skill_file=discovered.relative_skill_file,
                expected_name=discovered.expected_name,
            )
            if isinstance(parsed, SkillValidationIssue):
                issues.append(parsed)
            else:
                headers.append(parsed)

        return SkillHeaderDiscoveryResult.create(headers=headers, issues=issues)
