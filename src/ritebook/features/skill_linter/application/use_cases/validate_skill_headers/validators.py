"""Validation helpers for Agent Skill headers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

from ritebook.features.skill_linter.application.dtos import (
    FrontmatterMapping,
    ParsedSkillHeader,
    SkillValidationIssue,
)
from ritebook.shared_kernel import contains_terminal_control_characters

ALLOWED_FRONTMATTER_FIELDS = frozenset(
    {
        "allowed-tools",
        "compatibility",
        "description",
        "license",
        "metadata",
        "name",
    },
)
VALID_SKILL_NAME_PATTERN = re.compile(r"^(?!.*--)[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500


def validate_header(header: ParsedSkillHeader) -> tuple[SkillValidationIssue, ...]:
    """Validate a parsed skill header and return discovered issues."""
    frontmatter = header.frontmatter
    if not isinstance(frontmatter, Mapping):
        return (_issue(header, "frontmatter must be a mapping."),)
    frontmatter_mapping = cast("FrontmatterMapping", frontmatter)

    issues = [
        *_validate_top_level_fields(header, frontmatter_mapping),
        *_validate_name(header, frontmatter_mapping),
        *_validate_description(header, frontmatter_mapping),
        *_validate_optional_string(header, frontmatter_mapping, "license"),
        *_validate_compatibility(header, frontmatter_mapping),
        *_validate_metadata(header, frontmatter_mapping),
        *_validate_optional_string(header, frontmatter_mapping, "allowed-tools"),
    ]
    return tuple(issues)


def _validate_top_level_fields(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    issues: list[SkillValidationIssue] = []
    if any(not isinstance(key, str) for key in frontmatter):
        issues.append(_issue(header, "frontmatter keys must be strings."))
    if any(
        isinstance(key, str) and key not in ALLOWED_FRONTMATTER_FIELDS
        for key in frontmatter
    ):
        issues.append(_issue(header, "frontmatter contains unsupported fields."))
    return tuple(issues)


def _validate_name(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    if "name" not in frontmatter:
        return (_issue(header, "name is required."),)
    name = frontmatter["name"]
    if not isinstance(name, str):
        return (_issue(header, "name must be a string."),)

    issues: list[SkillValidationIssue] = []
    if not VALID_SKILL_NAME_PATTERN.fullmatch(name):
        issues.append(
            _issue(
                header,
                "name must be valid kebab-case: 1-64 lowercase ASCII letters, "
                "digits, and hyphens; no leading, trailing, or consecutive hyphens.",
            ),
        )
    if name != header.expected_name:
        issues.append(
            _issue(
                header,
                f"name must match skill directory name '{header.expected_name}'.",
            ),
        )
    return tuple(issues)


def _validate_description(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    if "description" not in frontmatter:
        return (_issue(header, "description is required."),)
    description = frontmatter["description"]
    if not isinstance(description, str):
        return (_issue(header, "description must be a string."),)
    if not description.strip():
        return (_issue(header, "description must not be blank."),)
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return (_issue(header, "description must be at most 1024 characters."),)
    if contains_terminal_control_characters(description):
        return (
            _issue(
                header,
                "description must not contain terminal control characters.",
            ),
        )
    return ()


def _validate_optional_string(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
    field_name: str,
) -> tuple[SkillValidationIssue, ...]:
    if field_name not in frontmatter:
        return ()
    if not isinstance(frontmatter[field_name], str):
        return (_issue(header, f"{field_name} must be a string."),)
    return ()


def _validate_compatibility(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    if "compatibility" not in frontmatter:
        return ()
    compatibility = frontmatter["compatibility"]
    if not isinstance(compatibility, str):
        return (_issue(header, "compatibility must be a string."),)
    if not compatibility.strip():
        return (_issue(header, "compatibility must not be blank."),)
    if len(compatibility) > MAX_COMPATIBILITY_LENGTH:
        return (_issue(header, "compatibility must be at most 500 characters."),)
    return ()


def _validate_metadata(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    if "metadata" not in frontmatter:
        return ()
    metadata = frontmatter["metadata"]
    if not isinstance(metadata, Mapping):
        return (_issue(header, "metadata must be a mapping."),)
    if any(not isinstance(key, str) for key in metadata):
        return (_issue(header, "metadata keys must be strings."),)
    if any(not isinstance(value, str) for value in metadata.values()):
        return (_issue(header, "metadata values must be strings."),)
    return ()


def _issue(header: ParsedSkillHeader, message: str) -> SkillValidationIssue:
    return SkillValidationIssue(skill_file=header.skill_file, message=message)
