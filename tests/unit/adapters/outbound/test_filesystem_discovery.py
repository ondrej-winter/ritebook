from pathlib import Path

import pytest

from ritebook.adapters.outbound.filesystem import (
    SkillFileReadError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
    discover_skill_files,
    read_skill_file_text,
)


def test_discover_skill_files_returns_sorted_filesystem_facts(tmp_path: Path) -> None:
    write_skill(tmp_path / "zeta" / "SKILL.md", "# Zeta\n")
    write_skill(tmp_path / "group" / "alpha" / "SKILL.md", "# Alpha\n")

    discovered = discover_skill_files(tmp_path)

    assert [
        (skill.expected_name, skill.relative_skill_dir, skill.relative_skill_file)
        for skill in discovered
    ] == [
        ("alpha", "group/alpha", "group/alpha/SKILL.md"),
        ("zeta", "zeta", "zeta/SKILL.md"),
    ]


def test_discover_skill_files_skips_hidden_directories(tmp_path: Path) -> None:
    write_skill(tmp_path / "visible" / "SKILL.md", "# Visible\n")
    write_skill(tmp_path / ".hidden" / "SKILL.md", "# Hidden\n")
    write_skill(tmp_path / "visible" / ".nested-hidden" / "SKILL.md", "# Hidden\n")

    discovered = discover_skill_files(tmp_path)

    assert [skill.relative_skill_dir for skill in discovered] == ["visible"]


def test_discover_skill_files_supports_root_skill_directory(tmp_path: Path) -> None:
    write_skill(tmp_path / "SKILL.md", "# Root\n")

    discovered = discover_skill_files(tmp_path)

    assert [
        (skill.expected_name, skill.relative_skill_dir, skill.relative_skill_file)
        for skill in discovered
    ] == [(tmp_path.name, ".", "SKILL.md")]


def test_discover_skill_files_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(SkillsRootNotFoundError, match="does not exist"):
        discover_skill_files(tmp_path / "missing")


def test_discover_skill_files_rejects_non_directory_root(tmp_path: Path) -> None:
    file_root = tmp_path / "not-a-directory"
    file_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(SkillsRootNotDirectoryError, match="not a directory"):
        discover_skill_files(file_root)


def test_read_skill_file_text_reads_utf8_content(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# Dovednost\n", encoding="utf-8")

    assert read_skill_file_text(skill_file) == "# Dovednost\n"


def test_read_skill_file_text_wraps_read_errors(tmp_path: Path) -> None:
    with pytest.raises(
        SkillFileReadError,
        match="Unable to read discovered skill file",
    ):
        read_skill_file_text(tmp_path / "missing" / "SKILL.md")


def write_skill(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
