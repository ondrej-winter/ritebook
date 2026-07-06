from pathlib import Path

import pytest

from ritebook.features.publisher.adapters.outbound.filesystem import (
    FilesystemSkillDiscovery,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)


def test_discover_skills_finds_nested_skill_directories(tmp_path: Path) -> None:
    write_skill(tmp_path / "zeta" / "SKILL.md", "# Zeta Skill\n")
    write_skill(tmp_path / "group" / "alpha" / "SKILL.md", "# Alpha Skill\n")

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert [
        (entry.name, entry.path, entry.skill_file, entry.title) for entry in entries
    ] == [
        ("alpha", "group/alpha", "group/alpha/SKILL.md", "Alpha Skill"),
        ("zeta", "zeta", "zeta/SKILL.md", "Zeta Skill"),
    ]


def test_discover_skills_skips_hidden_directories(tmp_path: Path) -> None:
    write_skill(tmp_path / "visible" / "SKILL.md", "# Visible Skill\n")
    write_skill(tmp_path / ".hidden" / "SKILL.md", "# Hidden Skill\n")
    write_skill(
        tmp_path / "visible" / ".nested-hidden" / "SKILL.md",
        "# Nested Hidden\n",
    )

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert [entry.path for entry in entries] == ["visible"]


def test_discover_skills_uses_none_when_title_is_missing(tmp_path: Path) -> None:
    write_skill(tmp_path / "untitled" / "SKILL.md", "## Not a title\nBody\n")

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert entries[0].title is None


def test_discover_skills_uses_first_markdown_h1_title(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "titled" / "SKILL.md",
        "Intro\n# First Title\n# Second Title\n",
    )

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert entries[0].title == "First Title"


def test_discover_skills_supports_root_skill_directory(tmp_path: Path) -> None:
    write_skill(tmp_path / "SKILL.md", "# Root Skill\n")

    entries = FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert [
        (entry.name, entry.path, entry.skill_file, entry.title) for entry in entries
    ] == [
        (tmp_path.name, ".", "SKILL.md", "Root Skill"),
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
