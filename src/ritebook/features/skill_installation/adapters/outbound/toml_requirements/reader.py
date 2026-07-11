"""Read and validate TOML skill installation requirements."""

import re
import tomllib
from pathlib import Path
from typing import Any, cast

from ritebook.features.skill_installation.application.dtos import (
    SkillReference,
    SkillRequirement,
    SkillRequirements,
)
from ritebook.features.skill_installation.application.errors import (
    RequirementsReadError,
)

ROOT_FIELDS = frozenset({"targets", "skills"})
SKILL_FIELDS = frozenset({"name", "target", "target_path"})
TARGET_NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class TomlRequirementsReader:
    """TOML-backed adapter for installation requirements files."""

    def read_requirements(self, requirements_file: str) -> SkillRequirements:
        """Read a requirements file and return application-owned DTOs."""
        data = _read_toml(requirements_file)
        _require_fields(data, ROOT_FIELDS, context="requirements file")

        targets = _parse_targets(data.get("targets"))
        skills = _parse_skills(data.get("skills"), targets, requirements_file)
        return SkillRequirements(targets=targets, skills=skills)


def _read_toml(requirements_file: str) -> dict[str, Any]:
    try:
        with Path(requirements_file).open("rb") as file:
            data = tomllib.load(file)
    except FileNotFoundError as err:
        msg = f"requirements file does not exist: {requirements_file}"
        raise RequirementsReadError(msg) from err
    except OSError as err:
        msg = f"requirements file cannot be read: {requirements_file}"
        raise RequirementsReadError(msg) from err
    except tomllib.TOMLDecodeError as err:
        msg = f"requirements file is invalid TOML: {requirements_file}"
        raise RequirementsReadError(msg) from err

    if not isinstance(data, dict):
        msg = "requirements file root must be a table"
        raise RequirementsReadError(msg)
    return data


def _parse_targets(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        msg = "[targets] must be a table"
        raise RequirementsReadError(msg)
    target_values = cast("dict[str, object]", value)

    targets: dict[str, str] = {}
    for nickname, target_path in target_values.items():
        if not TARGET_NICKNAME_PATTERN.fullmatch(nickname):
            msg = (
                "target nickname must contain only ASCII letters, digits, "
                "underscores, or hyphens"
            )
            raise RequirementsReadError(msg)
        if not isinstance(target_path, str) or not target_path:
            msg = f"target {nickname} must be a non-empty string path"
            raise RequirementsReadError(msg)
        targets[nickname] = target_path
    return targets


def _parse_skills(
    value: object,
    targets: dict[str, str],
    requirements_file: str,
) -> tuple[SkillRequirement, ...]:
    if not isinstance(value, list):
        msg = "[[skills]] must be an array of tables"
        raise RequirementsReadError(msg)

    skills: list[SkillRequirement] = []
    for entry in value:
        if not isinstance(entry, dict):
            msg = "each [[skills]] entry must be a table"
            raise RequirementsReadError(msg)
        skill_entry = cast("dict[str, Any]", entry)
        _require_fields(skill_entry, SKILL_FIELDS, context="skill entry")
        skills.append(_parse_skill(skill_entry, targets, requirements_file))
    return tuple(skills)


def _parse_skill(
    entry: dict[str, Any],
    targets: dict[str, str],
    requirements_file: str,
) -> SkillRequirement:
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        msg = "skill entry name must be a non-empty string"
        raise RequirementsReadError(msg)
    try:
        SkillReference.parse(name)
    except ValueError as err:
        raise RequirementsReadError(str(err)) from err

    target = _optional_string(entry, "target")
    target_path = _optional_string(entry, "target_path")
    if (target is None) == (target_path is None):
        msg = "skill entries must define exactly one of target or target_path"
        raise RequirementsReadError(msg)
    if target is not None and target not in targets:
        msg = f"target nickname {target} is not defined in {requirements_file}"
        raise RequirementsReadError(msg)

    try:
        return SkillRequirement(name=name, target=target, target_path=target_path)
    except ValueError as err:
        raise RequirementsReadError(str(err)) from err


def _optional_string(entry: dict[str, Any], field_name: str) -> str | None:
    value = entry.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        msg = f"skill entry {field_name} must be a non-empty string"
        raise RequirementsReadError(msg)
    return value


def _require_fields(
    value: dict[str, Any],
    allowed_fields: frozenset[str],
    *,
    context: str,
) -> None:
    unknown_fields = sorted(set(value) - allowed_fields)
    if unknown_fields:
        unknown = ", ".join(unknown_fields)
        msg = f"unknown field in {context}: {unknown}"
        raise RequirementsReadError(msg)
