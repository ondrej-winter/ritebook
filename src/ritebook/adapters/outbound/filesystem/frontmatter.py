"""YAML frontmatter parsing helpers for filesystem adapters."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from ritebook.adapters.outbound.filesystem.exceptions import SkillFileReadError

FRONTMATTER_DELIMITER = "---"
FRONTMATTER_START_LINE_INDEX = 0
FRONTMATTER_CONTENT_START_LINE_INDEX = FRONTMATTER_START_LINE_INDEX + 1
MAX_FRONTMATTER_LINE_COUNT = 200


@dataclass(frozen=True)
class FrontmatterParseError:
    """Adapter-level error for invalid or missing YAML frontmatter."""

    message: str


def parse_yaml_frontmatter(skill_file: Path) -> object | FrontmatterParseError:
    """Parse YAML frontmatter from the bounded header section of a skill file."""
    lines = _bounded_frontmatter_lines(skill_file)
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


def _bounded_frontmatter_lines(skill_file: Path) -> list[str]:
    lines: list[str] = []
    try:
        with skill_file.open(encoding="utf-8") as file:
            for _ in range(MAX_FRONTMATTER_LINE_COUNT + 1):
                line = file.readline()
                if line == "":
                    break
                lines.append(line.rstrip("\r\n"))
                if len(lines) > FRONTMATTER_CONTENT_START_LINE_INDEX and (
                    lines[-1] == FRONTMATTER_DELIMITER
                ):
                    break
    except (OSError, UnicodeError) as err:
        msg = f"Unable to read discovered skill file: {skill_file}"
        raise SkillFileReadError(msg) from err

    if len(lines) > MAX_FRONTMATTER_LINE_COUNT:
        return [FRONTMATTER_DELIMITER, *lines[FRONTMATTER_CONTENT_START_LINE_INDEX:]]
    return lines


def _closing_delimiter_index(lines: list[str]) -> int | None:
    for index, line in enumerate(
        lines[FRONTMATTER_CONTENT_START_LINE_INDEX:],
        start=FRONTMATTER_CONTENT_START_LINE_INDEX,
    ):
        if line == FRONTMATTER_DELIMITER:
            return index
    return None
