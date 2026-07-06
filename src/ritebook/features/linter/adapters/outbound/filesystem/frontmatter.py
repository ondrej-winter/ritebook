"""Frontmatter parsing helpers for filesystem skill headers."""

from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    FrontmatterParseError,
    parse_yaml_frontmatter,
)
from ritebook.features.linter.application.dtos import (
    ParsedSkillHeader,
    SkillValidationIssue,
)


def parse_skill_header(
    skill_file: Path,
    *,
    relative_skill_file: str,
    expected_name: str,
) -> ParsedSkillHeader | SkillValidationIssue:
    """Parse bounded YAML frontmatter from a discovered skill file."""
    frontmatter = parse_yaml_frontmatter(skill_file)
    if isinstance(frontmatter, FrontmatterParseError):
        return _issue(relative_skill_file, frontmatter.message)

    return ParsedSkillHeader(
        skill_file=relative_skill_file,
        expected_name=expected_name,
        frontmatter=frontmatter,
    )


def _issue(skill_file: str, message: str) -> SkillValidationIssue:
    return SkillValidationIssue(skill_file=skill_file, message=message)
