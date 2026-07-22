from pathlib import Path

import pytest

from ritebook.features.publisher.adapters.outbound.filesystem import (
    FilesystemSkillDiscovery,
)
from ritebook.features.publisher.application.errors import PublishIndexDiscoveryError


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


@pytest.mark.parametrize(
    ("relative_path", "expected_message"),
    [
        ("BadCollection/skill", "non-canonical identifier segment"),
        ("collection/nested/skill", "one or two segments"),
    ],
)
def test_discover_skills_rejects_invalid_catalog_paths_before_frontmatter(
    tmp_path: Path,
    relative_path: str,
    expected_message: str,
) -> None:
    write_skill(tmp_path / relative_path / "SKILL.md", "not valid frontmatter")

    with pytest.raises(PublishIndexDiscoveryError, match=expected_message) as err:
        FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert err.value.__cause__ is not None


def test_discover_skills_rejects_mixed_skill_collection_node(tmp_path: Path) -> None:
    write_skill(tmp_path / "quality" / "SKILL.md", skill_content(name="quality"))
    write_skill(
        tmp_path / "quality" / "code-review" / "SKILL.md",
        skill_content(name="code-review"),
    )

    with pytest.raises(PublishIndexDiscoveryError, match="both a root skill") as err:
        FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert "quality/code-review" in str(err.value)
    assert err.value.__cause__ is not None


def test_discover_skills_rejects_missing_description(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "undocumented" / "SKILL.md",
        "---\nname: undocumented\n---\n# Not the source of truth\n",
    )

    with pytest.raises(PublishIndexDiscoveryError, match="required description"):
        FilesystemSkillDiscovery().discover_skills(str(tmp_path))


def test_discover_skills_rejects_description_that_is_not_text(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path / "invalid-description" / "SKILL.md",
        "---\nname: invalid-description\ndescription: 123\n---\n",
    )

    with pytest.raises(PublishIndexDiscoveryError, match="required description"):
        FilesystemSkillDiscovery().discover_skills(str(tmp_path))


def test_discover_skills_rejects_invalid_frontmatter(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path / "invalid-frontmatter" / "SKILL.md",
        "---\nname: [unterminated\n---\n# Not the source of truth\n",
    )

    with pytest.raises(PublishIndexDiscoveryError, match="required description"):
        FilesystemSkillDiscovery().discover_skills(str(tmp_path))


def test_discover_skills_translates_skill_file_read_errors(tmp_path: Path) -> None:
    skill_file = tmp_path / "invalid-encoding" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_bytes(b"---\ndescription: \xff\n---\n")

    with pytest.raises(PublishIndexDiscoveryError, match="Unable to read") as err:
        FilesystemSkillDiscovery().discover_skills(str(tmp_path))

    assert err.value.__cause__ is not None


def test_discover_skills_rejects_skill_file_directly_at_skills_root(
    tmp_path: Path,
) -> None:
    skill_root = tmp_path / "root-skill"
    write_skill(skill_root / "SKILL.md", skill_content(name="root-skill"))

    with pytest.raises(PublishIndexDiscoveryError, match="literal relative POSIX"):
        FilesystemSkillDiscovery().discover_skills(str(skill_root))


def test_discover_skills_rejects_missing_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"

    with pytest.raises(PublishIndexDiscoveryError, match="does not exist") as err:
        FilesystemSkillDiscovery().discover_skills(str(missing_root))
    assert err.value.__cause__ is not None


def test_discover_skills_rejects_non_directory_root(tmp_path: Path) -> None:
    file_root = tmp_path / "not-a-directory"
    file_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(PublishIndexDiscoveryError, match="not a directory") as err:
        FilesystemSkillDiscovery().discover_skills(str(file_root))
    assert err.value.__cause__ is not None


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
