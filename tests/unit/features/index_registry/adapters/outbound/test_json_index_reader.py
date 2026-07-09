import json
from pathlib import Path

import pytest

from ritebook.features.index_registry.adapters.outbound.json_index import (
    JsonIndexReader,
)
from ritebook.features.index_registry.application.errors import (
    InvalidPublishedIndexError,
)


def test_json_index_reader_reads_valid_root_index(tmp_path: Path) -> None:
    write_index(tmp_path, {"index": {"name": "company-skills"}})

    result = JsonIndexReader().read_index(str(tmp_path))

    assert result.published_name == "company-skills"
    assert result.schema_version == 1
    assert result.skill_count == 1
    assert result.cacheable_content.endswith("\n")


def test_json_index_reader_accepts_repository_style_published_name(
    tmp_path: Path,
) -> None:
    write_index(tmp_path, {"index": {"name": "ondrej-winter/ritebook-shelf"}})

    result = JsonIndexReader().read_index(str(tmp_path))

    assert result.published_name == "ondrej-winter/ritebook-shelf"


def test_json_index_reader_requires_root_index(tmp_path: Path) -> None:
    with pytest.raises(InvalidPublishedIndexError, match="repository root"):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_rejects_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "ritebook-index.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(InvalidPublishedIndexError, match="not valid JSON"):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_rejects_missing_index_metadata(tmp_path: Path) -> None:
    write_index(tmp_path, {"index": None})

    with pytest.raises(InvalidPublishedIndexError, match="index metadata"):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_rejects_unsupported_schema(tmp_path: Path) -> None:
    write_index(tmp_path, {"schema_version": 2, "index": {"name": "company-skills"}})

    with pytest.raises(
        InvalidPublishedIndexError,
        match="unsupported index schema_version: 2",
    ):
        JsonIndexReader().read_index(str(tmp_path))


@pytest.mark.parametrize("bad_path", ["/absolute", "nested\\skill", "../escape"])
def test_json_index_reader_rejects_unsafe_skill_paths(
    tmp_path: Path,
    bad_path: str,
) -> None:
    write_index(
        tmp_path,
        {
            "index": {"name": "company-skills"},
            "skills": [
                {"name": "alpha", "path": bad_path, "skill_file": "alpha/SKILL.md"},
            ],
        },
    )

    with pytest.raises(InvalidPublishedIndexError, match="safe relative POSIX path"):
        JsonIndexReader().read_index(str(tmp_path))


def write_index(tmp_path: Path, overrides: dict[str, object]) -> None:
    payload = {
        "schema_version": 1,
        "index": {"name": "company-skills"},
        "generated_at": "2026-07-08T18:00:00Z",
        "skills_root": ".",
        "skills": [
            {"name": "alpha", "path": "alpha", "skill_file": "alpha/SKILL.md"},
        ],
    }
    payload.update(overrides)
    (tmp_path / "ritebook-index.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
