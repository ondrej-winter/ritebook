"""YAML frontmatter parsing helpers for filesystem adapters."""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from typing import TYPE_CHECKING, override

import yaml

from ritebook.adapters.outbound.filesystem.exceptions import SkillFileReadError

if TYPE_CHECKING:
    from collections.abc import Hashable
    from pathlib import Path
    from typing import BinaryIO

FRONTMATTER_DELIMITER = "---"
FRONTMATTER_START_LINE_INDEX = 0
FRONTMATTER_CONTENT_START_LINE_INDEX = FRONTMATTER_START_LINE_INDEX + 1
MAX_FRONTMATTER_BYTE_COUNT = 64 * 1024


@dataclass(frozen=True)
class FrontmatterParseError:
    """Adapter-level error for invalid or missing YAML frontmatter."""

    message: str


class _DuplicateMappingKeyError(yaml.YAMLError):
    """Raised when YAML contains an ambiguous duplicate mapping key."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate keys in every mapping."""

    @override
    def construct_mapping(
        self,
        node: yaml.nodes.MappingNode,
        deep: bool = False,
    ) -> dict[Hashable, object]:
        mapping: dict[Hashable, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as err:
                raise yaml.YAMLError from err
            if duplicate:
                raise _DuplicateMappingKeyError
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def parse_yaml_frontmatter(skill_file: Path) -> object | FrontmatterParseError:
    """Parse size-bounded YAML frontmatter and validate the file as UTF-8."""
    lines_or_error = _read_frontmatter_lines(skill_file)
    if isinstance(lines_or_error, FrontmatterParseError):
        return lines_or_error
    lines = lines_or_error
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
        frontmatter = _parse_unique_yaml(
            "\n".join(lines[FRONTMATTER_CONTENT_START_LINE_INDEX:closing_index]),
        )
    except _DuplicateMappingKeyError:
        return FrontmatterParseError(
            "frontmatter must not contain duplicate mapping keys.",
        )
    except yaml.YAMLError:
        return FrontmatterParseError("frontmatter must be valid YAML.")
    return frontmatter


def _parse_unique_yaml(content: str) -> object:
    loader = _UniqueKeySafeLoader(content)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def _read_frontmatter_lines(
    skill_file: Path,
) -> list[str] | FrontmatterParseError:
    lines: list[str] = []
    byte_count = 0
    try:
        with skill_file.open("rb") as file:
            while True:
                remaining = MAX_FRONTMATTER_BYTE_COUNT - byte_count
                raw_line = file.readline(remaining + 1)
                if len(raw_line) > remaining:
                    return _frontmatter_size_error()
                if not raw_line:
                    break
                byte_count += len(raw_line)
                lines.append(raw_line.decode("utf-8").rstrip("\r\n"))
                if len(lines) > FRONTMATTER_CONTENT_START_LINE_INDEX and (lines[-1] == FRONTMATTER_DELIMITER):
                    _validate_remaining_utf8(file)
                    break
                if byte_count == MAX_FRONTMATTER_BYTE_COUNT:
                    return _frontmatter_size_error()
    except (OSError, UnicodeError) as err:
        msg = f"Unable to read discovered skill file: {skill_file}"
        raise SkillFileReadError(msg) from err
    return lines


def _validate_remaining_utf8(file: BinaryIO) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")()
    while chunk := file.read(8192):
        decoder.decode(chunk)
    decoder.decode(b"", final=True)


def _frontmatter_size_error() -> FrontmatterParseError:
    return FrontmatterParseError(
        f"frontmatter must be at most {MAX_FRONTMATTER_BYTE_COUNT} UTF-8 bytes.",
    )


def _closing_delimiter_index(lines: list[str]) -> int | None:
    for index, line in enumerate(
        lines[FRONTMATTER_CONTENT_START_LINE_INDEX:],
        start=FRONTMATTER_CONTENT_START_LINE_INDEX,
    ):
        if line == FRONTMATTER_DELIMITER:
            return index
    return None
