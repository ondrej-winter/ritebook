import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

from ritebook.features.publisher.adapters.outbound.json_index import JsonIndexWriter
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


def read_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
