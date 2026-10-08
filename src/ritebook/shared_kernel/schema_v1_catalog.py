"""Pure strict schema-v1 catalog parsing and semantic validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ritebook.shared_kernel.catalog_paths import (
    CatalogPathValidationError,
    validate_catalog_path,
    validate_catalog_paths,
)
from ritebook.shared_kernel.identifiers import require_index_name
from ritebook.shared_kernel.portable_paths import (
    validate_portable_relative_posix_path,
)
from ritebook.shared_kernel.strict_json import (
    JsonValue,
    StrictJsonError,
    parse_strict_json_bytes,
)
from ritebook.shared_kernel.text_safety import normalize_portable_description
from ritebook.shared_kernel.timestamps import parse_canonical_utc_timestamp

if TYPE_CHECKING:
    from datetime import datetime

SCHEMA_V1 = 1
MAX_SCHEMA_V1_SKILL_ENTRIES = 10_000
ROOT_MEMBERS = frozenset(
    {"schema_version", "index", "generated_at", "skills_root", "skills"},
)
INDEX_MEMBERS = frozenset({"name"})
SKILL_MEMBERS = frozenset({"name", "path", "skill_file", "description"})


class SchemaV1CatalogError(ValueError):
    """Report a strict schema-v1 catalog contract violation."""


@dataclass(frozen=True, order=True)
class SchemaV1Skill:
    """One validated portable schema-v1 skill entry."""

    name: str
    path: str
    skill_file: str
    description: str


@dataclass(frozen=True)
class SchemaV1Catalog:
    """One validated portable schema-v1 catalog."""

    published_name: str
    generated_at: datetime
    skills_root: str
    skills: tuple[SchemaV1Skill, ...]
    schema_version: int = SCHEMA_V1


def parse_schema_v1_catalog_bytes(content: bytes) -> SchemaV1Catalog:
    """Parse exact bytes into a fully validated schema-v1 catalog."""
    try:
        value = parse_strict_json_bytes(content)
    except StrictJsonError as err:
        raise SchemaV1CatalogError(str(err)) from err
    root = _require_object(value, object_name="ritebook-index.json root")
    _require_exact_members(root, expected=ROOT_MEMBERS, object_name="root object")

    schema_version = root["schema_version"]
    if type(schema_version) is not int or schema_version != SCHEMA_V1:
        msg = f"unsupported index schema_version: {schema_version}"
        raise SchemaV1CatalogError(msg)

    index = _require_object(root["index"], object_name="index")
    _require_exact_members(index, expected=INDEX_MEMBERS, object_name="index object")
    published_name = _require_string(index["name"], field_name="index.name")
    generated_at_text = _require_string(
        root["generated_at"],
        field_name="generated_at",
    )
    skills_root = _require_string(root["skills_root"], field_name="skills_root")
    raw_skills = root["skills"]
    if not isinstance(raw_skills, list):
        msg = "ritebook-index.json skills must be an array."
        raise SchemaV1CatalogError(msg)
    if len(raw_skills) > MAX_SCHEMA_V1_SKILL_ENTRIES:
        msg = "ritebook-index.json skills must contain at most 10,000 entries."
        raise SchemaV1CatalogError(msg)

    try:
        require_index_name(published_name, field_name="Published index name")
        generated_at = parse_canonical_utc_timestamp(
            generated_at_text,
            field_name="generated_at",
        )
        validate_portable_relative_posix_path(
            skills_root,
            field_name="skills_root",
            allow_current_directory=True,
        )
        skills = tuple(_validate_skill(value) for value in raw_skills)
        validate_catalog_paths(skill.path for skill in skills)
    except CatalogPathValidationError as err:
        msg = f"invalid schema-v1 catalog structure: {err}"
        raise SchemaV1CatalogError(msg) from err
    except ValueError as err:
        raise SchemaV1CatalogError(str(err)) from err

    return SchemaV1Catalog(
        published_name=published_name,
        generated_at=generated_at,
        skills_root=skills_root,
        skills=skills,
    )


def _validate_skill(value: JsonValue) -> SchemaV1Skill:
    entry = _require_object(value, object_name="skill entry")
    _require_exact_members(entry, expected=SKILL_MEMBERS, object_name="skill entry")
    name = _require_string(entry["name"], field_name="skill name")
    path = _require_string(entry["path"], field_name="skill path")
    skill_file = _require_string(entry["skill_file"], field_name="skill_file")
    description = _require_string(entry["description"], field_name="description")

    catalog_path = validate_catalog_path(path)
    if name != catalog_path.skill_name:
        msg = "Skill entry name must match the final path segment."
        raise SchemaV1CatalogError(msg)
    validate_portable_relative_posix_path(path, field_name="skill path")
    validate_portable_relative_posix_path(skill_file, field_name="skill_file")
    if skill_file != f"{path}/SKILL.md":
        msg = "Skill entry skill_file must be exactly path/SKILL.md."
        raise SchemaV1CatalogError(msg)
    normalized_description = normalize_portable_description(
        description,
        field_name="Skill entry description",
    )
    if normalized_description != description:
        msg = "Skill entry description must be normalized without edge whitespace."
        raise SchemaV1CatalogError(msg)
    return SchemaV1Skill(
        name=name,
        path=PurePosixPath(path).as_posix(),
        skill_file=PurePosixPath(skill_file).as_posix(),
        description=description,
    )


def _require_object(
    value: JsonValue,
    *,
    object_name: str,
) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        msg = f"{object_name} must be a JSON object."
        raise SchemaV1CatalogError(msg)
    return value


def _require_exact_members(
    value: dict[str, JsonValue],
    *,
    expected: frozenset[str],
    object_name: str,
) -> None:
    actual = value.keys()
    missing = expected - actual
    if missing:
        msg = f"{object_name} is missing required members."
        raise SchemaV1CatalogError(msg)
    unknown = actual - expected
    if unknown:
        msg = f"{object_name} contains unknown members."
        raise SchemaV1CatalogError(msg)


def _require_string(value: JsonValue, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        msg = f"{field_name} must be a non-empty string."
        raise SchemaV1CatalogError(msg)
    return value
