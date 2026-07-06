"""YAML frontmatter parsing helpers for filesystem adapters."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from ritebook.adapters.outbound.filesystem.discovery import read_skill_file_text

FRONTMATTER_DELIMITER = "---"
FRONTMATTER_START_LINE_INDEX = 0
FRONTMATTER_CONTENT_START_LINE_INDEX = FRONTMATTER_START_LINE_INDEX + 1


@dataclass(frozen=True)
class FrontmatterParseError:
    """Adapter-level error for invalid or missing YAML frontmatter."""

    message: str


def parse_yaml_frontmatter(skill_file: Path) -> object | FrontmatterParseError:
    """Parse bounded YAML frontmatter from a skill file."""
    lines = read_skill_file_text(skill_file).splitlines()
    if not lines or lines[FRONTMATTER_START_LINE_INDEX] != FRONTMATTER_DELIMITER:
        return FrontmatterParseError(
            "frontmatter must start on the first line with ---.",
        )

    closing_index = _closing_delimiter_index(lines)
    if closing_index is None:
        return FrontmatterParseError(
            "frontmatter must include a closing --- delimiter.",
        )

    try:
        frontmatter: object = yaml.safe_load(
            "\n".join(lines[FRONTMATTER_CONTENT_START_LINE_INDEX:closing_index]),
        )
    except yaml.YAMLError as err:
        return FrontmatterParseError(f"frontmatter must be valid YAML: {err}")
    return frontmatter


def _closing_delimiter_index(lines: list[str]) -> int | None:
    for index, line in enumerate(
        lines[FRONTMATTER_CONTENT_START_LINE_INDEX:],
        start=FRONTMATTER_CONTENT_START_LINE_INDEX,
    ):
        if line == FRONTMATTER_DELIMITER:
            return index
    return None
