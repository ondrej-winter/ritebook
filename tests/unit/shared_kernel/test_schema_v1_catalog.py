import json
from datetime import UTC, datetime

import pytest

from ritebook.shared_kernel.schema_v1_catalog import (
    MAX_SCHEMA_V1_SKILL_ENTRIES,
    SchemaV1CatalogError,
    parse_schema_v1_catalog_bytes,
)


def test_parse_schema_v1_catalog_bytes_returns_validated_catalog() -> None:
    catalog = parse_schema_v1_catalog_bytes(_catalog_bytes())

    assert catalog.published_name == "company-skills"
    assert catalog.generated_at == datetime(2026, 7, 8, 18, 0, tzinfo=UTC)
    assert catalog.skills_root == "skills"
    assert catalog.skills[0].name == "code-review"
    assert catalog.skills[0].path == "quality/code-review"
    assert catalog.skills[0].skill_file == "quality/code-review/SKILL.md"
    assert catalog.skills[0].description == "Helps review code."


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ((), {"extension": True}),
        (("index",), {"extension": True}),
        (("skills", 0), {"extension": True}),
    ],
)
def test_parse_schema_v1_catalog_bytes_rejects_unknown_members(
    path: tuple[str | int, ...],
    value: dict[str, object],
) -> None:
    payload = _catalog_payload()
    target: object = payload
    for part in path:
        target = target[part]  # type: ignore[index]
    assert isinstance(target, dict)
    target.update(value)

    with pytest.raises(SchemaV1CatalogError, match="unknown members"):
        parse_schema_v1_catalog_bytes(json.dumps(payload).encode())


@pytest.mark.parametrize(
    "field_name",
    ["schema_version", "index", "generated_at", "skills_root", "skills"],
)
def test_parse_schema_v1_catalog_bytes_rejects_missing_root_members(
    field_name: str,
) -> None:
    payload = _catalog_payload()
    del payload[field_name]

    with pytest.raises(SchemaV1CatalogError, match="missing required members"):
        parse_schema_v1_catalog_bytes(json.dumps(payload).encode())


def test_parse_schema_v1_catalog_bytes_rejects_skill_count_above_limit() -> None:
    payload = _catalog_payload()
    skill = payload["skills"][0]  # type: ignore[index]
    payload["skills"] = [skill] * (MAX_SCHEMA_V1_SKILL_ENTRIES + 1)

    with pytest.raises(SchemaV1CatalogError, match="at most 10,000"):
        parse_schema_v1_catalog_bytes(json.dumps(payload).encode())


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("generated_at", "2026-07-08T18:00:00+00:00"),
        ("skills_root", "CON"),
    ],
)
def test_parse_schema_v1_catalog_bytes_rejects_non_portable_root_metadata(
    field_name: str,
    value: object,
) -> None:
    payload = _catalog_payload()
    payload[field_name] = value

    with pytest.raises(SchemaV1CatalogError):
        parse_schema_v1_catalog_bytes(json.dumps(payload).encode())


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("name", "other-skill"),
        ("skill_file", "quality/code-review/docs/SKILL.md"),
        ("description", " Helps review code. "),
        ("description", "x" * 1025),
    ],
)
def test_parse_schema_v1_catalog_bytes_rejects_incoherent_skill_entries(
    field_name: str,
    value: object,
) -> None:
    payload = _catalog_payload()
    payload["skills"][0][field_name] = value  # type: ignore[index]

    with pytest.raises(SchemaV1CatalogError):
        parse_schema_v1_catalog_bytes(json.dumps(payload).encode())


def test_parse_schema_v1_catalog_bytes_rejects_mixed_catalog_nodes() -> None:
    payload = _catalog_payload()
    payload["skills"] = [
        _skill("quality"),
        _skill("quality/code-review"),
    ]

    with pytest.raises(SchemaV1CatalogError, match="catalog structure"):
        parse_schema_v1_catalog_bytes(json.dumps(payload).encode())


def _catalog_bytes() -> bytes:
    return json.dumps(_catalog_payload()).encode()


def _catalog_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "index": {"name": "company-skills"},
        "generated_at": "2026-07-08T18:00:00Z",
        "skills_root": "skills",
        "skills": [_skill("quality/code-review")],
    }


def _skill(path: str) -> dict[str, str]:
    name = path.rsplit("/", maxsplit=1)[-1]
    return {
        "name": name,
        "path": path,
        "skill_file": f"{path}/SKILL.md",
        "description": "Helps review code.",
    }
