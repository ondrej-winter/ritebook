from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    FrontmatterParseError,
    parse_yaml_frontmatter,
)
from ritebook.adapters.outbound.filesystem.frontmatter import (
    MAX_FRONTMATTER_BYTE_COUNT,
)


def test_parse_yaml_frontmatter_returns_mapping(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "---\nname: code-review\ndescription: Helps review code.\n---\n# Body\n",
        encoding="utf-8",
    )

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert frontmatter == {
        "description": "Helps review code.",
        "name": "code-review",
    }


def test_parse_yaml_frontmatter_rejects_missing_opening_delimiter(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("name: code-review\n---\n# Body\n", encoding="utf-8")

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must start on the first line with ---."


def test_parse_yaml_frontmatter_accepts_more_than_two_hundred_lines(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    metadata = "\n".join(f"  key-{index}: value" for index in range(250))
    skill_file.write_text(
        (f"---\nname: code-review\ndescription: Helps review code.\nmetadata:\n{metadata}\n---\n# Body\n"),
        encoding="utf-8",
    )

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, dict)
    assert frontmatter["name"] == "code-review"


def test_parse_yaml_frontmatter_rejects_missing_closing_delimiter_within_bound(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("---\nname: code-review\n", encoding="utf-8")

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must include a closing --- delimiter."


def test_parse_yaml_frontmatter_accepts_exact_byte_limit(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    prefix = b"---\nname: code-review\ndescription: "
    suffix = b"\n---\n"
    value = b"x" * (MAX_FRONTMATTER_BYTE_COUNT - len(prefix) - len(suffix))
    skill_file.write_bytes(prefix + value + suffix + b"# Body\n")

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, dict)
    assert len(frontmatter["description"]) == len(value)


def test_parse_yaml_frontmatter_counts_utf8_bytes_at_limit(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    prefix = b"---\nname: code-review\ndescription: "
    suffix = b"\n---\n"
    remaining = MAX_FRONTMATTER_BYTE_COUNT - len(prefix) - len(suffix)
    value = "é" * (remaining // 2)
    skill_file.write_text(
        f"---\nname: code-review\ndescription: {value}x\n---\n",
        encoding="utf-8",
    )

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must be at most 65536 UTF-8 bytes."


def test_parse_yaml_frontmatter_rejects_frontmatter_over_byte_limit(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    oversized_value = "x" * MAX_FRONTMATTER_BYTE_COUNT
    skill_file.write_text(
        f"---\nname: code-review\ndescription: {oversized_value}\n---\n",
        encoding="utf-8",
    )

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must be at most 65536 UTF-8 bytes."


def test_parse_yaml_frontmatter_rejects_duplicate_mapping_keys(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "---\nname: code-review\nname: other\ndescription: Helps review code.\n---\n",
        encoding="utf-8",
    )

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must not contain duplicate mapping keys."


def test_parse_yaml_frontmatter_rejects_nested_duplicate_mapping_keys(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        (
            "---\nname: code-review\ndescription: Helps review code.\n"
            "metadata:\n  author: first\n  author: second\n---\n"
        ),
        encoding="utf-8",
    )

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must not contain duplicate mapping keys."


def test_parse_yaml_frontmatter_rejects_malformed_yaml_without_source_details(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "---\nsecret-field: [unterminated\n---\n# Body\n",
        encoding="utf-8",
    )

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must be valid YAML."
    assert "secret-field" not in frontmatter.message
