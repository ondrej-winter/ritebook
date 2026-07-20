"""JSON implementation of skill index writing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ritebook.features.publisher.application.errors import PublishIndexWriteError

if TYPE_CHECKING:
    from ritebook.features.publisher.domain import SkillCatalog, SkillEntry


class JsonIndexWriter:
    """Write skill catalogs as schema v1 JSON index files."""

    def write_index(self, catalog: SkillCatalog, output_path: str) -> None:
        """Write a deterministic, pretty-printed JSON index file."""
        try:
            Path(output_path).write_text(
                json.dumps(_catalog_to_json(catalog), indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as err:
            msg = f"Unable to write JSON skill index: {output_path}"
            raise PublishIndexWriteError(msg) from err


def _catalog_to_json(catalog: SkillCatalog) -> dict[str, Any]:
    return {
        "schema_version": catalog.schema_version,
        "index": {"name": catalog.index_name},
        "generated_at": _generated_at(catalog.generated_at),
        "skills_root": catalog.skills_root,
        "skills": [_entry_to_json(entry) for entry in catalog.skills],
    }


def _entry_to_json(entry: SkillEntry) -> dict[str, str]:
    return {
        "name": entry.name,
        "path": entry.path,
        "skill_file": entry.skill_file,
        "description": entry.description,
    }


def _generated_at(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
