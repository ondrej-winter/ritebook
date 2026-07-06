"""Validation helpers for Agent Skill headers."""

from __future__ import annotations

import re
from collections.abc import Mapping

from ritebook.features.linter.application.dtos import (
    FrontmatterMapping,
    ParsedSkillHeader,
    SkillValidationIssue,
)

VALID_SKILL_NAME_PATTERN = re.compile(r"^(?!.*--)[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
MAX_DESCRIPTION_LENGTH = 1024


def validate_header(header: ParsedSkillHeader) -> tuple[SkillValidationIssue, ...]:
    """Validate a parsed skill header and return discovered issues."""
    frontmatter = header.frontmatter
    if not isinstance(frontmatter, Mapping):
        return (_issue(header, "frontmatter must be a mapping."),)

    issues = [
        *_validate_name(header, frontmatter),
        *_validate_description(header, frontmatter),
        *_validate_metadata(header, frontmatter),
    ]
    return tuple(issues)


def _validate_name(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    name = frontmatter.get("name")
    if name is None:
        return (_issue(header, "name is required."),)
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
    description = frontmatter.get("description")
    if description is None:
        return (_issue(header, "description is required."),)
    if not isinstance(description, str):
        return (_issue(header, "description must be a string."),)
    if not description:
        return (_issue(header, "description must not be empty."),)
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return (_issue(header, "description must be at most 1024 characters."),)
    return ()


def _validate_metadata(
    header: ParsedSkillHeader,
    frontmatter: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    metadata = frontmatter.get("metadata")
    if metadata is None:
        return (_issue(header, "metadata is required."),)
    if not isinstance(metadata, Mapping):
        return (_issue(header, "metadata must be a mapping."),)

    issues: list[SkillValidationIssue] = []
    version = metadata.get("version")
    if version is None:
        issues.append(_issue(header, "metadata.version is required."))
    elif not isinstance(version, str):
        issues.append(_issue(header, "metadata.version must be a string."))

    dependencies = metadata.get("dependencies")
    if dependencies is None:
        issues.append(_issue(header, "metadata.dependencies is required."))
    elif not isinstance(dependencies, Mapping):
        issues.append(_issue(header, "metadata.dependencies must be a mapping."))
    else:
        issues.extend(_validate_dependencies(header, dependencies))
    return tuple(issues)


def _validate_dependencies(
    header: ParsedSkillHeader,
    dependencies: FrontmatterMapping,
) -> tuple[SkillValidationIssue, ...]:
    issues: list[SkillValidationIssue] = []
    tools = dependencies.get("tools")
    if tools is None:
        issues.append(_issue(header, "metadata.dependencies.tools is required."))
    elif not isinstance(tools, list):
        issues.append(_issue(header, "metadata.dependencies.tools must be a list."))
    else:
        issues.extend(
            _validate_dependency_entries(
                header,
                entries=tools,
                field_path="metadata.dependencies.tools",
            ),
        )

    skills = dependencies.get("skills")
    if skills is None:
        issues.append(_issue(header, "metadata.dependencies.skills is required."))
    elif not isinstance(skills, list):
        issues.append(_issue(header, "metadata.dependencies.skills must be a list."))
    else:
        issues.extend(
            _validate_dependency_entries(
                header,
                entries=skills,
                field_path="metadata.dependencies.skills",
            ),
        )
    return tuple(issues)


def _validate_dependency_entries(
    header: ParsedSkillHeader,
    *,
    entries: list[object],
    field_path: str,
) -> tuple[SkillValidationIssue, ...]:
    issues: list[SkillValidationIssue] = []
    for index, entry in enumerate(entries):
        entry_path = f"{field_path}[{index}]"
        if not isinstance(entry, Mapping):
            issues.append(_issue(header, f"{entry_path} must be a mapping."))
            continue

        issues.extend(
            _validate_required_text_field(header, entry, f"{entry_path}.name"),
        )
        issues.extend(
            _validate_required_text_field(header, entry, f"{entry_path}.purpose"),
        )
        issues.extend(
            _validate_required_boolean_field(header, entry, f"{entry_path}.required"),
        )
    return tuple(issues)


def _validate_required_text_field(
    header: ParsedSkillHeader,
    entry: FrontmatterMapping,
    field_path: str,
) -> tuple[SkillValidationIssue, ...]:
    value = entry.get(field_path.rsplit(".", maxsplit=1)[-1])
    if value is None:
        return (_issue(header, f"{field_path} is required."),)
    if not isinstance(value, str):
        return (_issue(header, f"{field_path} must be a string."),)
    if not value:
        return (_issue(header, f"{field_path} must not be empty."),)
    return ()


def _validate_required_boolean_field(
    header: ParsedSkillHeader,
    entry: FrontmatterMapping,
    field_path: str,
) -> tuple[SkillValidationIssue, ...]:
    value = entry.get(field_path.rsplit(".", maxsplit=1)[-1])
    if value is None:
        return (_issue(header, f"{field_path} is required."),)
    if not isinstance(value, bool):
        return (_issue(header, f"{field_path} must be a boolean."),)
    return ()


def _issue(header: ParsedSkillHeader, message: str) -> SkillValidationIssue:
    return SkillValidationIssue(skill_file=header.skill_file, message=message)
