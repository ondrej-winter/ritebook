from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    FrontmatterParseError,
    parse_yaml_frontmatter,
)
from ritebook.adapters.outbound.filesystem.frontmatter import (
    MAX_FRONTMATTER_LINE_COUNT,
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


def test_parse_yaml_frontmatter_rejects_missing_closing_delimiter_within_bound(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    content = "---\n" + "\n".join(
        f"line_{index}: value" for index in range(MAX_FRONTMATTER_LINE_COUNT)
    )
    skill_file.write_text(content, encoding="utf-8")

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must include a closing --- delimiter."


def test_parse_yaml_frontmatter_does_not_parse_beyond_frontmatter_bound(
    tmp_path: Path,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    content = "---\n" + "\n".join(
        f"line_{index}: value" for index in range(MAX_FRONTMATTER_LINE_COUNT + 1)
    )
    skill_file.write_text(content, encoding="utf-8")

    frontmatter = parse_yaml_frontmatter(skill_file)

    assert isinstance(frontmatter, FrontmatterParseError)
    assert frontmatter.message == "frontmatter must include a closing --- delimiter."
