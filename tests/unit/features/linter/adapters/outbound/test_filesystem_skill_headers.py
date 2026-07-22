from pathlib import Path

import pytest

from ritebook.features.linter.adapters.outbound.filesystem import (
    FilesystemSkillHeaderDiscovery,
)
from ritebook.features.linter.application.errors import LintSkillsDiscoveryError


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


def test_discover_headers_reports_zero_segment_candidate_before_frontmatter(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path / "SKILL.md", "not valid frontmatter")

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert result.headers == ()
    assert [issue.format() for issue in result.issues] == [
        "SKILL.md: Catalog path is not a literal relative POSIX path: '.'.",
    ]


def test_discover_headers_reports_invalid_and_over_deep_paths_deterministically(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path / "valid" / "SKILL.md",
        frontmatter(name="valid"),
    )
    write_skill(
        tmp_path / "BadCollection" / "skill" / "SKILL.md",
        "not valid frontmatter",
    )
    write_skill(
        tmp_path / "collection" / "nested" / "skill" / "SKILL.md",
        "not valid frontmatter",
    )

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert [header.skill_file for header in result.headers] == ["valid/SKILL.md"]
    assert [issue.format() for issue in result.issues] == [
        "BadCollection/skill/SKILL.md: Catalog path contains a non-canonical "
        "identifier segment: 'BadCollection/skill'.",
        "collection/nested/skill/SKILL.md: Catalog path must contain one or two "
        "segments: 'collection/nested/skill'.",
    ]


def test_discover_headers_reports_every_mixed_skill_collection_child(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path / "quality" / "SKILL.md", frontmatter(name="quality"))
    write_skill(
        tmp_path / "quality" / "alpha" / "SKILL.md",
        frontmatter(name="alpha"),
    )
    write_skill(
        tmp_path / "quality" / "zeta" / "SKILL.md",
        frontmatter(name="zeta"),
    )

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert [header.skill_file for header in result.headers] == ["quality/SKILL.md"]
    assert [issue.format() for issue in result.issues] == [
        "quality/alpha/SKILL.md: Catalog node cannot be both a root skill and a "
        "collection: 'quality' conflicts with 'quality/alpha'.",
        "quality/zeta/SKILL.md: Catalog node cannot be both a root skill and a "
        "collection: 'quality' conflicts with 'quality/zeta'.",
    ]


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


def test_discover_headers_rejects_skill_file_directly_at_skills_root(
    tmp_path: Path,
) -> None:
    write_skill(tmp_path / "SKILL.md", frontmatter(name=tmp_path.name))

    result = FilesystemSkillHeaderDiscovery().discover_headers(str(tmp_path))

    assert result.headers == ()
    assert [issue.format() for issue in result.issues] == [
        "SKILL.md: Catalog path is not a literal relative POSIX path: '.'.",
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

    with pytest.raises(LintSkillsDiscoveryError, match="does not exist") as err:
        FilesystemSkillHeaderDiscovery().discover_headers(str(missing_root))
    assert err.value.__cause__ is not None


def test_discover_headers_rejects_non_directory_root(tmp_path: Path) -> None:
    file_root = tmp_path / "not-a-directory"
    file_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(LintSkillsDiscoveryError, match="not a directory") as err:
        FilesystemSkillHeaderDiscovery().discover_headers(str(file_root))
    assert err.value.__cause__ is not None


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
