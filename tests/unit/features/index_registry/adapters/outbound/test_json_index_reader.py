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


def test_json_index_reader_reads_cached_skills_by_exact_path(tmp_path: Path) -> None:
    cached_index_path = tmp_path / "custom-cache.json"
    write_index_file(
        cached_index_path,
        {
            "skills": [
                {
                    "name": "alpha",
                    "path": "alpha",
                    "skill_file": "alpha/SKILL.md",
                    "description": "Alpha helps with planning.",
                },
                {
                    "name": "beta",
                    "path": "nested/beta",
                    "skill_file": "nested/beta/SKILL.md",
                },
            ],
        },
    )

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert [skill.name for skill in result] == ["alpha", "beta"]
    assert result[0].path == "alpha"
    assert result[0].skill_file == "alpha/SKILL.md"
    assert result[0].description == "Alpha helps with planning."


def test_json_index_reader_exposes_relative_skills_root_for_installation(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    cached_index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "index": {"name": "company-skills"},
                "skills_root": "skills",
                "skills": [
                    {
                        "name": "alpha",
                        "path": "software-development/alpha",
                        "skill_file": "software-development/alpha/SKILL.md",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert result[0].source_root == "skills"


def test_json_index_reader_ignores_absolute_skills_root_for_installation(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    cached_index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "index": {"name": "company-skills"},
                "skills_root": str(tmp_path / "skills"),
                "skills": [
                    {
                        "name": "alpha",
                        "path": "alpha",
                        "skill_file": "alpha/SKILL.md",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert result[0].source_root == "."


def test_json_index_reader_reads_empty_cached_skills(tmp_path: Path) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(cached_index_path, {"skills": []})

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert result == ()


def test_json_index_reader_rejects_slash_separated_published_name(
    tmp_path: Path,
) -> None:
    write_index(tmp_path, {"index": {"name": "ondrej-winter/ritebook-shelf"}})

    with pytest.raises(InvalidPublishedIndexError, match="Published index name"):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_requires_root_index(tmp_path: Path) -> None:
    with pytest.raises(InvalidPublishedIndexError, match="repository root"):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_requires_cached_index_file(tmp_path: Path) -> None:
    with pytest.raises(
        InvalidPublishedIndexError,
        match=r"cached ritebook-index\.json",
    ):
        JsonIndexReader().read_skills(str(tmp_path / "missing.json"))


def test_json_index_reader_rejects_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "ritebook-index.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(InvalidPublishedIndexError, match="not valid JSON"):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_rejects_cached_invalid_json(tmp_path: Path) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    cached_index_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(InvalidPublishedIndexError, match="not valid JSON"):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_rejects_cached_non_object_payload(tmp_path: Path) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    cached_index_path.write_text("[]", encoding="utf-8")

    with pytest.raises(InvalidPublishedIndexError, match="must contain a JSON object"):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_rejects_missing_index_metadata(tmp_path: Path) -> None:
    write_index(tmp_path, {"index": None})

    with pytest.raises(InvalidPublishedIndexError, match="index metadata"):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_read_skills_does_not_require_index_metadata(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(cached_index_path, {"index": None})

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert [skill.name for skill in result] == ["alpha"]


def test_json_index_reader_rejects_unsupported_schema(tmp_path: Path) -> None:
    write_index(tmp_path, {"schema_version": 2, "index": {"name": "company-skills"}})

    with pytest.raises(
        InvalidPublishedIndexError,
        match="unsupported index schema_version: 2",
    ):
        JsonIndexReader().read_index(str(tmp_path))


def test_json_index_reader_rejects_cached_unsupported_schema(tmp_path: Path) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(cached_index_path, {"schema_version": 2})

    with pytest.raises(
        InvalidPublishedIndexError,
        match="unsupported index schema_version: 2",
    ):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_rejects_cached_missing_skills(tmp_path: Path) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    payload = default_index_payload()
    del payload["skills"]
    cached_index_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InvalidPublishedIndexError, match="skills array"):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_rejects_cached_malformed_skills(tmp_path: Path) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(cached_index_path, {"skills": {"name": "alpha"}})

    with pytest.raises(InvalidPublishedIndexError, match="skills array"):
        JsonIndexReader().read_skills(str(cached_index_path))


@pytest.mark.parametrize(
    ("field_name", "bad_value", "message"),
    [
        ("name", "", "non-empty name"),
        ("name", "Not Kebab", "Skill name"),
        ("path", "", "non-empty path"),
        ("skill_file", "", "non-empty skill_file"),
        ("description", "", "description must be a non-empty string"),
    ],
)
def test_json_index_reader_rejects_cached_malformed_skill_entries(
    tmp_path: Path,
    field_name: str,
    bad_value: str,
    message: str,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    skill = {"name": "alpha", "path": "alpha", "skill_file": "alpha/SKILL.md"}
    skill[field_name] = bad_value
    write_index_file(cached_index_path, {"skills": [skill]})

    with pytest.raises(InvalidPublishedIndexError, match=message):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_rejects_cached_non_object_skill_entries(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(cached_index_path, {"skills": ["alpha"]})

    with pytest.raises(InvalidPublishedIndexError, match="JSON objects"):
        JsonIndexReader().read_skills(str(cached_index_path))


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


@pytest.mark.parametrize("bad_path", ["/absolute", "nested\\skill", "../escape"])
def test_json_index_reader_rejects_cached_unsafe_skill_paths(
    tmp_path: Path,
    bad_path: str,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(
        cached_index_path,
        {
            "skills": [
                {"name": "alpha", "path": bad_path, "skill_file": "alpha/SKILL.md"},
            ],
        },
    )

    with pytest.raises(InvalidPublishedIndexError, match="safe relative POSIX path"):
        JsonIndexReader().read_skills(str(cached_index_path))


def write_index(tmp_path: Path, overrides: dict[str, object]) -> None:
    write_index_file(tmp_path / "ritebook-index.json", overrides)


def write_index_file(index_path: Path, overrides: dict[str, object]) -> None:
    payload = default_index_payload()
    payload.update(overrides)
    index_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def default_index_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "index": {"name": "company-skills"},
        "generated_at": "2026-07-08T18:00:00Z",
        "skills_root": ".",
        "skills": [
            {"name": "alpha", "path": "alpha", "skill_file": "alpha/SKILL.md"},
        ],
    }
