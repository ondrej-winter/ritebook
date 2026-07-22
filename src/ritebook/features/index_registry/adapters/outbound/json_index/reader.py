"""Read and validate ritebook-index.json publisher indexes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

from ritebook.features.index_registry.application.dtos import (
    CachedSkillSummary,
    PublishedIndex,
)
from ritebook.features.index_registry.application.errors import (
    InvalidPublishedIndexError,
)
from ritebook.shared_kernel import (
    require_index_name,
    require_kebab_case_identifier,
    require_no_terminal_control_characters,
)
from ritebook.shared_kernel.catalog_paths import (
    CatalogPathValidationError,
    validate_catalog_paths,
)

CANONICAL_INDEX_FILENAME = "ritebook-index.json"


class JsonIndexReader:
    """Read published index metadata and cached skill summaries from JSON."""

    def read_index(self, content: bytes) -> PublishedIndex:
        """Validate exact committed root ritebook-index.json bytes."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as err:
            msg = "ritebook-index.json is not valid UTF-8"
            raise InvalidPublishedIndexError(msg) from err
        payload = _parse_json_object(text)
        digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
        return _validate_payload(payload, text, digest)

    def read_skills(self, cached_index_path: str) -> tuple[CachedSkillSummary, ...]:
        """Read validated skill summaries from an exact cached index file path."""
        _content, payload = _read_json_index(
            Path(cached_index_path),
            missing_message="cached ritebook-index.json was not found",
            unreadable_message="unable to read cached ritebook-index.json",
        )
        return _validate_cached_skills_payload(payload)


def _read_json_index(
    index_path: Path,
    *,
    missing_message: str,
    unreadable_message: str,
) -> tuple[str, dict[str, Any]]:
    try:
        content = index_path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise InvalidPublishedIndexError(missing_message) from err
    except OSError as err:
        raise InvalidPublishedIndexError(unreadable_message) from err
    return content, _parse_json_object(content)


def _parse_json_object(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as err:
        msg = "ritebook-index.json is not valid JSON"
        raise InvalidPublishedIndexError(msg) from err
    if not isinstance(payload, dict):
        msg = "ritebook-index.json must contain a JSON object"
        raise InvalidPublishedIndexError(msg)
    return cast("dict[str, Any]", payload)


def _validate_payload(
    payload: dict[str, Any],
    content: str,
    index_digest: str,
) -> PublishedIndex:
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        msg = f"unsupported index schema_version: {schema_version}"
        raise InvalidPublishedIndexError(msg)
    index = payload.get("index")
    if not isinstance(index, dict):
        msg = "ritebook-index.json is missing required index metadata"
        raise InvalidPublishedIndexError(msg)
    published_name = index.get("name")
    if not isinstance(published_name, str):
        msg = "ritebook-index.json is missing required index.name metadata"
        raise InvalidPublishedIndexError(msg)
    try:
        require_index_name(published_name, field_name="Published index name")
    except ValueError as err:
        raise InvalidPublishedIndexError(str(err)) from err
    skills = _validate_cached_skills_payload(payload)
    return PublishedIndex(
        published_name=published_name,
        schema_version=schema_version,
        skill_count=len(skills),
        cacheable_content=content,
        index_digest=index_digest,
    )


def _validate_cached_skills_payload(
    payload: dict[str, Any],
) -> tuple[CachedSkillSummary, ...]:
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        msg = f"unsupported index schema_version: {schema_version}"
        raise InvalidPublishedIndexError(msg)
    skills = payload.get("skills")
    if not isinstance(skills, list):
        msg = "ritebook-index.json must contain a skills array"
        raise InvalidPublishedIndexError(msg)
    raw_skills_root = payload.get("skills_root", ".")
    if not isinstance(raw_skills_root, str) or not raw_skills_root:
        msg = "ritebook-index.json skills_root must be a non-empty string when present"
        raise InvalidPublishedIndexError(msg)
    skills_root = _installable_source_root(raw_skills_root)
    validated_skills = tuple(
        _validate_skill_entry(skill, source_root=skills_root) for skill in skills
    )
    _validate_catalog_structure(validated_skills)
    return validated_skills


def _validate_catalog_structure(skills: tuple[CachedSkillSummary, ...]) -> None:
    try:
        validate_catalog_paths(skill.path for skill in skills)
    except CatalogPathValidationError as err:
        msg = (
            f"invalid schema-v1 catalog structure: {err} "
            "Reorganize skills into root or collection/skill paths and republish "
            "the index."
        )
        raise InvalidPublishedIndexError(msg) from err


def _validate_skill_entry(value: object, *, source_root: str) -> CachedSkillSummary:
    if not isinstance(value, dict):
        msg = "index skill entries must be JSON objects"
        raise InvalidPublishedIndexError(msg)
    entry = cast("dict[str, object]", value)
    for field_name in ("name", "path", "skill_file", "description"):
        field_value = entry.get(field_name)
        if not isinstance(field_value, str) or not field_value:
            msg = f"index skill entries must include non-empty {field_name}"
            raise InvalidPublishedIndexError(msg)
    name = cast("str", entry["name"])
    path = cast("str", entry["path"])
    skill_file = cast("str", entry["skill_file"])
    description = cast("str", entry["description"])
    try:
        require_kebab_case_identifier(name, field_name="Skill name")
        require_no_terminal_control_characters(
            description,
            field_name="index skill entry description",
        )
    except ValueError as err:
        raise InvalidPublishedIndexError(str(err)) from err
    _validate_relative_posix_path(path, field_name="path")
    _validate_relative_posix_path(skill_file, field_name="skill_file")
    _validate_skill_file_inside_path(skill_file=skill_file, path=path)
    return CachedSkillSummary(
        name=name,
        path=path,
        skill_file=skill_file,
        description=description,
        source_root=source_root,
    )


def _validate_relative_posix_path(value: str, *, field_name: str) -> None:
    try:
        require_no_terminal_control_characters(
            value,
            field_name=f"index skill entry {field_name}",
        )
    except ValueError as err:
        raise InvalidPublishedIndexError(str(err)) from err
    path = PurePosixPath(value)
    if value.startswith("/") or "\\" in value or ".." in path.parts:
        msg = f"index skill entry {field_name} must be a safe relative POSIX path"
        raise InvalidPublishedIndexError(msg)


def _validate_skill_file_inside_path(*, skill_file: str, path: str) -> None:
    try:
        PurePosixPath(skill_file).relative_to(PurePosixPath(path))
    except ValueError as err:
        msg = "index skill entry skill_file must be inside path"
        raise InvalidPublishedIndexError(msg) from err


def _installable_source_root(value: str) -> str:
    try:
        require_no_terminal_control_characters(value, field_name="skills_root")
    except ValueError as err:
        raise InvalidPublishedIndexError(str(err)) from err
    path = PurePosixPath(value)
    if path.is_absolute() or "\\" in value or ".." in path.parts:
        msg = "ritebook-index.json skills_root must be a safe relative POSIX path"
        raise InvalidPublishedIndexError(msg)
    return value
