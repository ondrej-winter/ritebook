from pathlib import Path

import pytest

from ritebook.features.publisher.adapters.outbound.filesystem import (
    FilesystemSkillDiscovery,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)


def test_discover_skills_finds_nested_skill_directories(tmp_path: Path) -> None:
    write_skill(tmp_path / "zeta" / "SKILL.md", skill_content(name="zeta-skill"))
    write_skill(
        tmp_path / "group" / "alpha" / "SKILL.md",
        skill_content(name="alpha-skill"),
    )

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert [
        (entry.name, entry.path, entry.skill_file, entry.description)
        for entry in entries
    ] == [
        (
            "alpha",
            "group/alpha",
            "group/alpha/SKILL.md",
            "Example skill",
        ),
        ("zeta", "zeta", "zeta/SKILL.md", "Example skill"),
    ]


def test_discover_skills_skips_hidden_directories(tmp_path: Path) -> None:
    write_skill(tmp_path / "visible" / "SKILL.md", skill_content(name="visible"))
    write_skill(tmp_path / ".hidden" / "SKILL.md", skill_content(name="hidden"))
    write_skill(
        tmp_path / "visible" / ".nested-hidden" / "SKILL.md",
        skill_content(name="nested-hidden"),
    )

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert [entry.path for entry in entries] == ["visible"]


def test_discover_skills_uses_none_when_description_is_missing(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "undocumented" / "SKILL.md",
        "---\nname: undocumented\n---\n# Not the source of truth\n",
    )

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert entries[0].description is None


def test_discover_skills_uses_none_when_description_is_not_text(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path / "invalid-description" / "SKILL.md",
        "---\nname: invalid-description\ndescription: 123\n---\n",
    )

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert entries[0].description is None


def test_discover_skills_uses_none_when_frontmatter_is_invalid(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path / "invalid-frontmatter" / "SKILL.md",
        "---\nname: [unterminated\n---\n# Not the source of truth\n",
    )

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert entries[0].description is None


def test_discover_skills_supports_root_skill_directory(tmp_path: Path) -> None:
    write_skill(tmp_path / "SKILL.md", skill_content(name="root-skill"))

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert [
        (entry.name, entry.path, entry.skill_file, entry.description)
        for entry in entries
    ] == [
        (tmp_path.name, ".", "SKILL.md", "Example skill"),
    ]


def test_discover_skills_rejects_missing_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"

    with pytest.raises(SkillsRootNotFoundError, match="does not exist"):
        FilesystemSkillDiscovery().discover_skills(str(missing_root))


def test_discover_skills_rejects_non_directory_root(tmp_path: Path) -> None:
    file_root = tmp_path / "not-a-directory"
    file_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(SkillsRootNotDirectoryError, match="not a directory"):
        FilesystemSkillDiscovery().discover_skills(str(file_root))


def write_skill(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def skill_content(*, name: str) -> str:
    return f"""---
name: {name}
description: Example skill
metadata:
  version: "1.0.0"
  dependencies:
    tools: []
    skills: []
---
"""
