import json
import os
import stat
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO, cast

import pytest

from ritebook.features.publisher.adapters.outbound.json_index import (
    JsonIndexWriter,
    writer,
)
from ritebook.features.publisher.application.errors import PublishIndexWriteError
from ritebook.features.publisher.domain import SkillCatalog, SkillEntry


def test_json_index_writer_writes_schema_v1_json(tmp_path: Path) -> None:
    output_path = tmp_path / "ritebook-index.json"
    catalog = SkillCatalog.create(
        index_name="company-skills",
        generated_at=datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
        skills_root="skills",
        skills=(
            SkillEntry(
                name="zeta",
                path="zeta",
                skill_file="zeta/SKILL.md",
                description="Zeta helps with publishing.",
            ),
            SkillEntry(
                name="alpha",
                path="alpha",
                skill_file="alpha/SKILL.md",
                description="Alpha helps with publishing.",
            ),
        ),
    )

    JsonIndexWriter().write_index(catalog, str(output_path))

    payload = read_json(output_path)
    assert payload == {
        "schema_version": 1,
        "index": {"name": "company-skills"},
        "generated_at": "2026-07-04T18:49:00Z",
        "skills_root": "skills",
        "skills": [
            {
                "name": "alpha",
                "path": "alpha",
                "skill_file": "alpha/SKILL.md",
                "description": "Alpha helps with publishing.",
            },
            {
                "name": "zeta",
                "path": "zeta",
                "skill_file": "zeta/SKILL.md",
                "description": "Zeta helps with publishing.",
            },
        ],
    }


def test_json_index_writer_pretty_prints_with_two_spaces(tmp_path: Path) -> None:
    output_path = tmp_path / "ritebook-index.json"
    catalog = SkillCatalog.create(
        index_name="company-skills",
        generated_at=datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
        skills_root=".",
        skills=(
            SkillEntry(
                name="alpha",
                path="alpha",
                skill_file="alpha/SKILL.md",
                description="Alpha helps with publishing.",
            ),
        ),
    )

    JsonIndexWriter().write_index(catalog, str(output_path))

    text = output_path.read_text(encoding="utf-8")
    assert '\n  "schema_version": 1,' in text
    assert "\n    {" in text
    assert text.endswith("\n")


def test_json_index_writer_normalizes_generated_at_to_utc(tmp_path: Path) -> None:
    output_path = tmp_path / "ritebook-index.json"
    catalog = SkillCatalog.create(
        index_name="company-skills",
        generated_at=datetime(
            2026,
            7,
            4,
            20,
            49,
            tzinfo=timezone(timedelta(hours=2)),
        ),
        skills_root="skills",
        skills=(),
    )

    JsonIndexWriter().write_index(catalog, str(output_path))

    payload = read_json(output_path)
    assert payload["generated_at"] == "2026-07-04T18:49:00Z"


def test_json_index_writer_overwrites_existing_file_when_called(tmp_path: Path) -> None:
    output_path = tmp_path / "ritebook-index.json"
    output_path.write_text("old content", encoding="utf-8")
    catalog = SkillCatalog.create(
        index_name="company-skills",
        generated_at=datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
        skills_root="skills",
        skills=(),
    )

    JsonIndexWriter().write_index(catalog, str(output_path))

    assert read_json(output_path)["skills"] == []


def test_json_index_writer_preserves_existing_file_when_serialization_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ritebook-index.json"
    output_path.write_text("old content", encoding="utf-8")

    def fail_serialization(*_args: object, **_kwargs: object) -> str:
        msg = "serialization failed"
        raise TypeError(msg)

    monkeypatch.setattr(writer.json, "dumps", fail_serialization)

    with pytest.raises(PublishIndexWriteError):
        JsonIndexWriter().write_index(empty_catalog(), str(output_path))

    assert output_path.read_text(encoding="utf-8") == "old content"
    assert temporary_index_paths(tmp_path) == []


def test_json_index_writer_preserves_existing_file_when_temporary_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ritebook-index.json"
    output_path.write_text("old content", encoding="utf-8")

    def fail_write(_file: BinaryIO, _content: bytes) -> None:
        msg = "write failed"
        raise OSError(msg)

    monkeypatch.setattr(writer, "_write_and_sync", fail_write)

    with pytest.raises(PublishIndexWriteError):
        JsonIndexWriter().write_index(empty_catalog(), str(output_path))

    assert output_path.read_text(encoding="utf-8") == "old content"
    assert temporary_index_paths(tmp_path) == []


def test_json_index_writer_preserves_existing_file_when_sync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ritebook-index.json"
    output_path.write_text("old content", encoding="utf-8")

    def fail_sync(_file_descriptor: int) -> None:
        msg = "sync failed"
        raise OSError(msg)

    monkeypatch.setattr(writer.os, "fsync", fail_sync)

    with pytest.raises(PublishIndexWriteError):
        JsonIndexWriter().write_index(empty_catalog(), str(output_path))

    assert output_path.read_text(encoding="utf-8") == "old content"
    assert temporary_index_paths(tmp_path) == []


def test_json_index_writer_preserves_existing_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ritebook-index.json"
    output_path.write_text("old content", encoding="utf-8")

    def fail_replace(_source: Path, _destination: Path) -> Path:
        msg = "replace failed"
        raise OSError(msg)

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(PublishIndexWriteError):
        JsonIndexWriter().write_index(empty_catalog(), str(output_path))

    assert output_path.read_text(encoding="utf-8") == "old content"
    assert temporary_index_paths(tmp_path) == []


def test_json_index_writer_rejects_symlinked_output_without_modifying_target(
    tmp_path: Path,
) -> None:
    external_path = tmp_path / "external-index.json"
    external_path.write_text("external content", encoding="utf-8")
    output_path = tmp_path / "ritebook-index.json"
    output_path.symlink_to(external_path)

    with pytest.raises(PublishIndexWriteError):
        JsonIndexWriter().write_index(empty_catalog(), str(output_path))

    assert output_path.is_symlink()
    assert external_path.read_text(encoding="utf-8") == "external content"
    assert temporary_index_paths(tmp_path) == []


def test_json_index_writer_rejects_symlinked_output_ancestor(
    tmp_path: Path,
) -> None:
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    external_path = external_directory / "ritebook-index.json"
    external_path.write_text("external content", encoding="utf-8")
    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(external_directory, target_is_directory=True)

    with pytest.raises(PublishIndexWriteError):
        JsonIndexWriter().write_index(
            empty_catalog(),
            str(linked_directory / "ritebook-index.json"),
        )

    assert external_path.read_text(encoding="utf-8") == "external content"
    assert temporary_index_paths(external_directory) == []


def test_json_index_writer_uses_unique_temporary_file_names(tmp_path: Path) -> None:
    output_path = tmp_path / "ritebook-index.json"
    stale_path = tmp_path / ".ritebook-index.json.stale.tmp"
    stale_path.write_text("stale content", encoding="utf-8")

    JsonIndexWriter().write_index(empty_catalog(), str(output_path))

    assert read_json(output_path)["skills"] == []
    assert stale_path.read_text(encoding="utf-8") == "stale content"
    assert temporary_index_paths(tmp_path) == [stale_path]


def test_json_index_writer_creates_permission_safe_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "ritebook-index.json"
    observed_mode: int | None = None

    def inspect_mode_then_fail(staged_file: BinaryIO, _content: bytes) -> None:
        nonlocal observed_mode
        observed_mode = stat.S_IMODE(os.fstat(staged_file.fileno()).st_mode)
        msg = "stop after inspecting mode"
        raise OSError(msg)

    monkeypatch.setattr(writer, "_write_and_sync", inspect_mode_then_fail)

    with pytest.raises(PublishIndexWriteError):
        JsonIndexWriter().write_index(empty_catalog(), str(output_path))

    assert observed_mode == 0o600
    assert temporary_index_paths(tmp_path) == []


def empty_catalog() -> SkillCatalog:
    return SkillCatalog.create(
        index_name="company-skills",
        generated_at=datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
        skills_root="skills",
        skills=(),
    )


def temporary_index_paths(directory: Path) -> list[Path]:
    return sorted(directory.glob(".ritebook-index.json.*.tmp"))


def read_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
