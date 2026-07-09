"""Read and validate root ritebook-index.json publisher indexes."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

from ritebook.features.index_registry.application.dtos import PublishedIndex
from ritebook.features.index_registry.application.errors import (
    InvalidPublishedIndexError,
)
from ritebook.shared_kernel import require_index_name, require_kebab_case_identifier

CANONICAL_INDEX_FILENAME = "ritebook-index.json"


class JsonIndexReader:
    """Read published index metadata from repository root JSON."""

    def read_index(self, repository_path: str) -> PublishedIndex:
        """Read and validate root ritebook-index.json from a repository path."""
        index_path = Path(repository_path) / CANONICAL_INDEX_FILENAME
        try:
            content = index_path.read_text(encoding="utf-8")
        except FileNotFoundError as err:
            msg = "ritebook-index.json was not found at the repository root"
            raise InvalidPublishedIndexError(msg) from err
        except OSError as err:
            msg = "unable to read ritebook-index.json at the repository root"
            raise InvalidPublishedIndexError(msg) from err
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as err:
            msg = "ritebook-index.json is not valid JSON"
            raise InvalidPublishedIndexError(msg) from err
        if not isinstance(payload, dict):
            msg = "ritebook-index.json must contain a JSON object"
            raise InvalidPublishedIndexError(msg)
        return _validate_payload(cast("dict[str, Any]", payload), content)


def _validate_payload(payload: dict[str, Any], content: str) -> PublishedIndex:
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
    skills = payload.get("skills")
    if not isinstance(skills, list):
        msg = "ritebook-index.json must contain a skills array"
        raise InvalidPublishedIndexError(msg)
    for skill in skills:
        _validate_skill_entry(skill)
    return PublishedIndex(
        published_name=published_name,
        schema_version=schema_version,
        skill_count=len(skills),
        cacheable_content=content if content.endswith("\n") else f"{content}\n",
    )


def _validate_skill_entry(value: object) -> None:
    if not isinstance(value, dict):
        msg = "index skill entries must be JSON objects"
        raise InvalidPublishedIndexError(msg)
    for field_name in ("name", "path", "skill_file"):
        if not isinstance(value.get(field_name), str) or not value[field_name]:
            msg = f"index skill entries must include non-empty {field_name}"
            raise InvalidPublishedIndexError(msg)
    try:
        require_kebab_case_identifier(str(value["name"]), field_name="Skill name")
    except ValueError as err:
        raise InvalidPublishedIndexError(str(err)) from err
    _validate_relative_posix_path(str(value["path"]), field_name="path")
    _validate_relative_posix_path(str(value["skill_file"]), field_name="skill_file")
    title = value.get("title")
    if title is not None and (not isinstance(title, str) or not title):
        msg = "index skill entry title must be a non-empty string when present"
        raise InvalidPublishedIndexError(msg)


def _validate_relative_posix_path(value: str, *, field_name: str) -> None:
    path = PurePosixPath(value)
    if value.startswith("/") or "\\" in value or ".." in path.parts:
        msg = f"index skill entry {field_name} must be a safe relative POSIX path"
        raise InvalidPublishedIndexError(msg)
