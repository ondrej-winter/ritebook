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


def test_json_index_reader_preserves_exact_committed_bytes() -> None:
    content = _catalog_bytes(description="Příliš žluťoučký kůň 検証 🔍.")

    result = JsonIndexReader().read_index(content)

    assert result.published_name == "company-skills"
    assert result.schema_version == 1
    assert result.skill_count == 1
    assert result.cacheable_content == content
    assert result.index_digest == _digest(content)


def test_json_index_reader_translates_strict_catalog_errors() -> None:
    with pytest.raises(InvalidPublishedIndexError, match="duplicate member names"):
        JsonIndexReader().read_index(
            b'{"schema_version":1,"schema_version":1}',
        )


def test_json_index_reader_adds_catalog_structure_remediation() -> None:
    content = _catalog_bytes().replace(
        b'"quality/code-review"',
        b'"quality/python/code-review"',
    )

    with pytest.raises(
        InvalidPublishedIndexError,
        match="Reorganize skills into root or collection/skill paths",
    ):
        JsonIndexReader().read_index(content)


def test_json_index_reader_verifies_cached_digest_before_parsing(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    cached_index_path.write_bytes(b"not-json")

    with pytest.raises(InvalidPublishedIndexError, match="digest"):
        JsonIndexReader().read_skills(
            str(cached_index_path),
            _digest(b"different"),
        )


def test_json_index_reader_parses_cached_bytes_after_digest_verification(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "custom-cache.json"
    content = _catalog_bytes(skills_root="skills")
    cached_index_path.write_bytes(content)

    result = JsonIndexReader().read_skills(
        str(cached_index_path),
        _digest(content),
    )

    assert len(result) == 1
    assert result[0].name == "code-review"
    assert result[0].path == "quality/code-review"
    assert result[0].skill_file == "quality/code-review/SKILL.md"
    assert result[0].description == "Helps review code."
    assert result[0].source_root == "skills"


def test_json_index_reader_translates_cached_parse_errors_after_digest_match(
    tmp_path: Path,
) -> None:
    cached_index_path = tmp_path / "ritebook-index.json"
    content = b"not-json"
    cached_index_path.write_bytes(content)

    with pytest.raises(InvalidPublishedIndexError, match="malformed"):
        JsonIndexReader().read_skills(
            str(cached_index_path),
            _digest(content),
        )


def test_json_index_reader_requires_cached_index_file(tmp_path: Path) -> None:
    with pytest.raises(
        InvalidPublishedIndexError,
        match=r"cached ritebook-index\.json",
    ):
        JsonIndexReader().read_skills(
            str(tmp_path / "missing.json"),
            _digest(b"missing"),
        )


def _catalog_bytes(
    *,
    description: str = "Helps review code.",
    skills_root: str = ".",
) -> bytes:
    return json.dumps(
        {
            "schema_version": 1,
            "index": {"name": "company-skills"},
            "generated_at": "2026-07-08T18:00:00Z",
            "skills_root": skills_root,
            "skills": [
                {
                    "name": "code-review",
                    "path": "quality/code-review",
                    "skill_file": "quality/code-review/SKILL.md",
                    "description": description,
                },
            ],
        },
        ensure_ascii=False,
        indent=2,
    ).encode()


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"
