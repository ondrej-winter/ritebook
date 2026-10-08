"""JSON implementation of skill index writing."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO

from ritebook.features.publisher.application.errors import PublishIndexWriteError
from ritebook.shared_kernel import format_canonical_utc_timestamp
from ritebook.shared_kernel.strict_json import MAX_STRICT_JSON_INPUT_BYTES

if TYPE_CHECKING:
    from ritebook.features.publisher.domain import SkillCatalog, SkillEntry


class JsonIndexWriter:
    """Write skill catalogs as schema v1 JSON index files."""

    def write_index(self, catalog: SkillCatalog, output_path: str) -> None:
        """Write a deterministic, pretty-printed JSON index file."""
        staged_path: Path | None = None
        try:
            content = json.dumps(_catalog_to_json(catalog), indent=2) + "\n"
            content_bytes = content.encode()
            _require_bounded_payload(content_bytes)
            destination = Path(output_path)
            _validate_destination(destination)
            staged_path, staged_file = _create_staged_file(destination)
            with staged_file:
                _write_and_sync(staged_file, content_bytes)
            _validate_destination(destination)
            staged_path.replace(destination)
            staged_path = None
        except (OSError, TypeError, ValueError) as err:
            msg = f"Unable to write JSON skill index: {output_path}"
            raise PublishIndexWriteError(msg) from err
        finally:
            if staged_path is not None:
                with suppress(OSError):
                    staged_path.unlink(missing_ok=True)


def _validate_destination(destination: Path) -> None:
    _reject_symlink_components(destination.parent)
    if not destination.parent.is_dir():
        msg = "index output parent must be a directory"
        raise OSError(msg)
    if destination.is_symlink():
        msg = "index output must not be a symlink"
        raise OSError(msg)
    if destination.exists() and not destination.is_file():
        msg = "index output must be a regular file"
        raise OSError(msg)


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts:
        if part == path.anchor:
            continue
        current /= part
        if current.is_symlink():
            msg = "index output path must not contain symlinks"
            raise OSError(msg)


def _create_staged_file(destination: Path) -> tuple[Path, BinaryIO]:
    file_descriptor, staged_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    return Path(staged_name), os.fdopen(file_descriptor, "wb")


def _write_and_sync(staged_file: BinaryIO, content: bytes) -> None:
    staged_file.write(content)
    staged_file.flush()
    os.fsync(staged_file.fileno())


def _require_bounded_payload(content: bytes) -> None:
    if len(content) > MAX_STRICT_JSON_INPUT_BYTES:
        msg = "Serialized schema-v1 index exceeds the 16 MiB size limit."
        raise ValueError(msg)


def _catalog_to_json(catalog: SkillCatalog) -> dict[str, Any]:
    return {
        "schema_version": catalog.schema_version,
        "index": {"name": catalog.index_name},
        "generated_at": format_canonical_utc_timestamp(
            catalog.generated_at,
            field_name="generated_at",
        ),
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
