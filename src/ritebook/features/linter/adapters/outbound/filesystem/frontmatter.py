"""Frontmatter parsing helpers for filesystem skill headers."""

from pathlib import Path

import yaml

from ritebook.features.linter.adapters.outbound.filesystem.exceptions import (
    SkillFileReadError,
)
from ritebook.features.linter.application.dtos import (
    ParsedSkillHeader,
    SkillValidationIssue,
)

FRONTMATTER_DELIMITER = "---"


def parse_skill_header(
    skill_file: Path,
    *,
    relative_skill_file: str,
    expected_name: str,
) -> ParsedSkillHeader | SkillValidationIssue:
    """Parse bounded YAML frontmatter from a discovered skill file."""
    lines = _read_skill_file(skill_file).splitlines()
    if not lines or lines[0] != FRONTMATTER_DELIMITER:
        return _issue(
            relative_skill_file,
            "frontmatter must start on the first line with ---.",
        )

    closing_index = _closing_delimiter_index(lines)
    if closing_index is None:
        return _issue(
            relative_skill_file,
            "frontmatter must include a closing --- delimiter.",
        )

    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:closing_index]))
    except yaml.YAMLError as err:
        return _issue(relative_skill_file, f"frontmatter must be valid YAML: {err}")

    return ParsedSkillHeader(
        skill_file=relative_skill_file,
        expected_name=expected_name,
        frontmatter=frontmatter,
    )


def _read_skill_file(skill_file: Path) -> str:
    try:
        return skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as err:
        msg = f"Unable to read discovered skill file: {skill_file}"
        raise SkillFileReadError(msg) from err


def _closing_delimiter_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[1:], start=1):
        if line == FRONTMATTER_DELIMITER:
            return index
    return None


def _issue(skill_file: str, message: str) -> SkillValidationIssue:
    return SkillValidationIssue(skill_file=skill_file, message=message)
