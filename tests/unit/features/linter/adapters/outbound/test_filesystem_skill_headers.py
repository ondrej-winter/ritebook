from pathlib import Path

import pytest

from ritebook.features.linter.adapters.outbound.filesystem import (
    FilesystemSkillHeaderDiscovery,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)


def test_discover_headers_parses_nested_skill_frontmatter(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "zeta" / "SKILL.md",
        frontmatter(name="zeta", description="Zeta skill."),
    )
    write_skill(
        tmp_path / "group" / "alpha" / "SKILL.md",
        frontmatter(name="alpha", description="Alpha skill."),
    )

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert result.issues == ()
    assert [(header.skill_file, header.expected_name) for header in result.headers] == [
        ("group/alpha/SKILL.md", "alpha"),
        ("zeta/SKILL.md", "zeta"),
    ]
    assert result.headers[0].frontmatter == {
        "name": "alpha",
        "description": "Alpha skill.",
        "metadata": {
            "version": "1.0.0",
            "dependencies": {
                "tools": [
                    {
                        "name": "git",
                        "purpose": "Inspect version-control state.",
                        "required": True,
                    },
                ],
                "skills": [],
            },
        },
    }


def test_discover_headers_skips_hidden_directories(tmp_path: Path) -> None:
    write_skill(tmp_path / "visible" / "SKILL.md", frontmatter(name="visible"))
    write_skill(tmp_path / ".hidden" / "SKILL.md", frontmatter(name="hidden"))
    write_skill(
        tmp_path / "visible" / ".nested-hidden" / "SKILL.md",
        frontmatter(name="nested-hidden"),
    )

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert [header.skill_file for header in result.headers] == ["visible/SKILL.md"]
    assert result.issues == ()


def test_discover_headers_supports_root_skill_directory(tmp_path: Path) -> None:
    write_skill(tmp_path / "SKILL.md", frontmatter(name=tmp_path.name))

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert [(header.skill_file, header.expected_name) for header in result.headers] == [
        ("SKILL.md", tmp_path.name),
    ]


@pytest.mark.parametrize(
    ("content", "expected_message"),
    [
        (
            "# Missing frontmatter\n",
            "frontmatter must start on the first line with ---.",
        ),
        (
            "---\nname: alpha\n# Missing close\n",
            "frontmatter must include a closing --- delimiter.",
        ),
        ("---\nname: [unterminated\n---\n", "frontmatter must be valid YAML"),
    ],
)
def test_discover_headers_reports_frontmatter_parse_issues(
    tmp_path: Path,
    content: str,
    expected_message: str,
) -> None:
    write_skill(tmp_path / "alpha" / "SKILL.md", content)

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert result.headers == ()
    assert len(result.issues) == 1
    assert result.issues[0].skill_file == "alpha/SKILL.md"
    assert result.issues[0].message.startswith(expected_message)


@pytest.mark.parametrize(
    ("content", "expected_frontmatter"),
    [
        ("---\n---\n# Empty\n", None),
        ("---\n- one\n- two\n---\n# List\n", ["one", "two"]),
    ],
)
def test_discover_headers_returns_non_mapping_frontmatter_for_application_validation(
    tmp_path: Path,
    content: str,
    expected_frontmatter: object,
) -> None:
    write_skill(tmp_path / "alpha" / "SKILL.md", content)

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert result.issues == ()
    assert result.headers[0].frontmatter == expected_frontmatter


def test_discover_headers_rejects_missing_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"

    with pytest.raises(SkillsRootNotFoundError, match="does not exist"):
        FilesystemSkillHeaderDiscovery().discover_headers(str(missing_root))


def test_discover_headers_rejects_non_directory_root(tmp_path: Path) -> None:
    file_root = tmp_path / "not-a-directory"
    file_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(SkillsRootNotDirectoryError, match="not a directory"):
        FilesystemSkillHeaderDiscovery().discover_headers(str(file_root))


def write_skill(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def frontmatter(name: str, description: str = "A visible skill.") -> str:
    return f"""---
name: {name}
description: {description}
metadata:
  version: "1.0.0"
  dependencies:
    tools:
      - name: git
        purpose: Inspect version-control state.
        required: true
    skills: []
---
# {name}
"""
