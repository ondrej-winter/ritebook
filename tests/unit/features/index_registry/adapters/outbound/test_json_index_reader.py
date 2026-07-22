import hashlib
import json
from pathlib import Path

import pytest

from ritebook.features.index_registry.adapters.outbound.json_index import (
    JsonIndexReader,
)
from ritebook.features.index_registry.application.errors import (
    InvalidPublishedIndexError,
)
from ritebook.shared_kernel.catalog_paths import (
    CatalogPathValidationError,
    CatalogPathValidationReason,
)


def test_json_index_reader_reads_valid_root_index(tmp_path: Path) -> None:
    write_index(tmp_path, {"index": {"name": "company-skills"}})
    content = (tmp_path / "ritebook-index.json").read_bytes()

    result = JsonIndexReader().read_index(content)

    assert result.published_name == "company-skills"
    assert result.schema_version == 1
    assert result.skill_count == 1
    assert result.cacheable_content.encode() == content
    assert result.index_digest == f"sha256:{hashlib.sha256(content).hexdigest()}"


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
                    "description": "Beta helps with planning.",
                },
            ],
        },
    )

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert [skill.name for skill in result] == ["alpha", "beta"]
    assert result[0].path == "alpha"
    assert result[0].skill_file == "alpha/SKILL.md"
    assert result[0].description == "Alpha helps with planning."


def test_json_index_reader_preserves_duplicate_names_at_distinct_paths(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(
        cached_index_path,
        {
            "skills": [
                {
                    "name": "code-review",
                    "path": "backend/code-review",
                    "skill_file": "backend/code-review/SKILL.md",
                    "description": "Backend code review.",
                },
                {
                    "name": "code-review",
                    "path": "frontend/code-review",
                    "skill_file": "frontend/code-review/SKILL.md",
                    "description": "Frontend code review.",
                },
            ],
        },
    )

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert [skill.name for skill in result] == ["code-review", "code-review"]
    assert [skill.path for skill in result] == [
        "backend/code-review",
        "frontend/code-review",
    ]


@pytest.mark.parametrize("read_cached", [False, True])
def test_json_index_reader_accepts_root_and_collection_child_catalog_paths(
    tmp_path: Path,
    *,
    read_cached: bool,
) -> None:
    index_path = tmp_path / "ritebook-index.json"
    write_index_file(
        index_path,
        {
            "skills": [
                skill_entry("code-review"),
                skill_entry("quality/runtime-verification"),
            ],
        },
    )

    if read_cached:
        result = JsonIndexReader().read_skills(str(index_path))
        assert [skill.path for skill in result] == [
            "code-review",
            "quality/runtime-verification",
        ]
    else:
        result = JsonIndexReader().read_index(index_path.read_bytes())
        assert result.skill_count == 2


@pytest.mark.parametrize("read_cached", [False, True])
@pytest.mark.parametrize(
    ("paths", "reason"),
    [
        (["quality//code-review"], CatalogPathValidationReason.MALFORMED_PATH),
        (["Quality/code-review"], CatalogPathValidationReason.INVALID_SEGMENT),
        (["quality/python/code-review"], CatalogPathValidationReason.INVALID_DEPTH),
        (
            ["quality/code-review", "quality/code-review"],
            CatalogPathValidationReason.DUPLICATE_PATH,
        ),
        (["quality", "quality/code-review"], CatalogPathValidationReason.MIXED_NODE),
    ],
)
def test_json_index_reader_rejects_invalid_schema_v1_catalog_paths(
    tmp_path: Path,
    *,
    read_cached: bool,
    paths: list[str],
    reason: CatalogPathValidationReason,
) -> None:
    index_path = tmp_path / "ritebook-index.json"
    write_index_file(
        index_path,
        {"skills": [skill_entry(path) for path in paths]},
    )

    reader = JsonIndexReader()
    with pytest.raises(
        InvalidPublishedIndexError,
        match=r"Reorganize skills.*republish the index",
    ) as exc_info:
        read_index(reader, index_path=index_path, read_cached=read_cached)

    cause = exc_info.value.__cause__
    assert isinstance(cause, CatalogPathValidationError)
    assert cause.reason is reason


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
                        "description": "Alpha helps with planning.",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert result[0].source_root == "skills"


@pytest.mark.parametrize(
    "bad_skills_root",
    ["/absolute", "../escape", "nested\\skills", ""],
)
def test_json_index_reader_rejects_unsafe_skills_root_for_installation(
    tmp_path: Path,
    bad_skills_root: str,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    cached_index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "index": {"name": "company-skills"},
                "skills_root": bad_skills_root,
                "skills": [
                    {
                        "name": "alpha",
                        "path": "alpha",
                        "skill_file": "alpha/SKILL.md",
                        "description": "Alpha helps with planning.",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    with pytest.raises(InvalidPublishedIndexError, match="skills_root"):
        JsonIndexReader().read_skills(str(cached_index_path))


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
        JsonIndexReader().read_index(committed_index_bytes(tmp_path))


def test_json_index_reader_requires_cached_index_file(tmp_path: Path) -> None:
    with pytest.raises(
        InvalidPublishedIndexError,
        match=r"cached ritebook-index\.json",
    ):
        JsonIndexReader().read_skills(str(tmp_path / "missing.json"))


def test_json_index_reader_rejects_invalid_json() -> None:
    with pytest.raises(InvalidPublishedIndexError, match="not valid JSON"):
        JsonIndexReader().read_index(b"not-json")


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
        JsonIndexReader().read_index(committed_index_bytes(tmp_path))


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
        JsonIndexReader().read_index(committed_index_bytes(tmp_path))


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
        ("description", "", "non-empty description"),
    ],
)
def test_json_index_reader_rejects_cached_malformed_skill_entries(
    tmp_path: Path,
    field_name: str,
    bad_value: str,
    message: str,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    skill = {
        "name": "alpha",
        "path": "alpha",
        "skill_file": "alpha/SKILL.md",
        "description": "Alpha helps with planning.",
    }
    skill[field_name] = bad_value
    write_index_file(cached_index_path, {"skills": [skill]})

    with pytest.raises(InvalidPublishedIndexError, match=message):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_rejects_cached_skill_without_description(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    skill = {
        "name": "alpha",
        "path": "alpha",
        "skill_file": "alpha/SKILL.md",
    }
    write_index_file(cached_index_path, {"skills": [skill]})

    with pytest.raises(InvalidPublishedIndexError, match="non-empty description"):
        JsonIndexReader().read_skills(str(cached_index_path))


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("description", "Safe prefix\nforged line"),
        ("description", "Safe prefix\x1b[31mred"),
        ("path", "alpha\tforged"),
        ("skill_file", "alpha/SKILL.md\x85forged"),
    ],
)
def test_json_index_reader_rejects_controls_in_cached_skill_fields(
    tmp_path: Path,
    field_name: str,
    bad_value: str,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    skill = {
        "name": "alpha",
        "path": "alpha",
        "skill_file": "alpha/SKILL.md",
        "description": "Alpha helps with planning.",
    }
    skill[field_name] = bad_value
    write_index_file(cached_index_path, {"skills": [skill]})

    with pytest.raises(
        InvalidPublishedIndexError,
        match=rf"{field_name} must not contain terminal control characters",
    ):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_preserves_readable_unicode_description(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    skill = {
        "name": "alpha",
        "path": "alpha",
        "skill_file": "alpha/SKILL.md",
        "description": "Příliš žluťoučký kůň 検証 🔍.",
    }
    write_index_file(cached_index_path, {"skills": [skill]})

    result = JsonIndexReader().read_skills(str(cached_index_path))

    assert result[0].description == skill["description"]


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
                {
                    "name": "alpha",
                    "path": bad_path,
                    "skill_file": "alpha/SKILL.md",
                    "description": "Alpha helps with planning.",
                },
            ],
        },
    )

    with pytest.raises(InvalidPublishedIndexError, match="safe relative POSIX path"):
        JsonIndexReader().read_index(committed_index_bytes(tmp_path))


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
                {
                    "name": "alpha",
                    "path": bad_path,
                    "skill_file": "alpha/SKILL.md",
                    "description": "Alpha helps with planning.",
                },
            ],
        },
    )

    with pytest.raises(InvalidPublishedIndexError, match="safe relative POSIX path"):
        JsonIndexReader().read_skills(str(cached_index_path))


def test_json_index_reader_rejects_skill_file_outside_skill_path(
    tmp_path: Path,
) -> None:
    write_index(
        tmp_path,
        {
            "index": {"name": "company-skills"},
            "skills": [
                {
                    "name": "alpha",
                    "path": "alpha",
                    "skill_file": "beta/SKILL.md",
                    "description": "Alpha helps with planning.",
                },
            ],
        },
    )

    with pytest.raises(InvalidPublishedIndexError, match="inside path"):
        JsonIndexReader().read_index(committed_index_bytes(tmp_path))


def test_json_index_reader_rejects_cached_skill_file_outside_skill_path(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    write_index_file(
        cached_index_path,
        {
            "skills": [
                {
                    "name": "alpha",
                    "path": "alpha",
                    "skill_file": "beta/SKILL.md",
                    "description": "Alpha helps with planning.",
                },
            ],
        },
    )

    with pytest.raises(InvalidPublishedIndexError, match="inside path"):
        JsonIndexReader().read_skills(str(cached_index_path))


def write_index(tmp_path: Path, overrides: dict[str, object]) -> None:
    write_index_file(tmp_path / "ritebook-index.json", overrides)


def committed_index_bytes(tmp_path: Path) -> bytes:
    return (tmp_path / "ritebook-index.json").read_bytes()


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
            {
                "name": "alpha",
                "path": "alpha",
                "skill_file": "alpha/SKILL.md",
                "description": "Alpha helps with planning.",
            },
        ],
    }


def skill_entry(path: str) -> dict[str, str]:
    name = path.rsplit("/", maxsplit=1)[-1]
    return {
        "name": name,
        "path": path,
        "skill_file": f"{path}/SKILL.md",
        "description": f"Helps with {name} workflows.",
    }


def read_index(
    reader: JsonIndexReader,
    *,
    index_path: Path,
    read_cached: bool,
) -> object:
    if read_cached:
        return reader.read_skills(str(index_path))
    return reader.read_index(index_path.read_bytes())
