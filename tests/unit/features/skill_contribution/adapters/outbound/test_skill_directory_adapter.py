import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from ritebook.features.skill_contribution.adapters.outbound.skill_directory import (
    FilesystemSkillDirectoryAdapter,
)
from ritebook.features.skill_contribution.application.dtos import SkillChangeStatus
from ritebook.features.skill_contribution.application.dtos.publish_skill_change import (
    ContributionLockfileEntry,
    ContributionWorkspace,
)
from ritebook.features.skill_contribution.application.errors import (
    MissingInstalledSkillTargetError,
    SkillContributionError,
    UnsafeContributionPathError,
)


def test_skill_directory_adapter_reports_identical_directories(tmp_path: Path) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)

    comparison = FilesystemSkillDirectoryAdapter().compare(entry, workspace)

    assert comparison.status is SkillChangeStatus.NO_CHANGES
    assert comparison.changed_file_count == 0


def test_skill_directory_adapter_reports_changed_file(tmp_path: Path) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    (tmp_path / "installed" / "code-review" / "SKILL.md").write_text(
        "changed",
        encoding="utf-8",
    )

    comparison = FilesystemSkillDirectoryAdapter().compare(entry, workspace)

    assert comparison.status is SkillChangeStatus.CHANGED
    assert comparison.changed_file_count == 1


def test_skill_directory_adapter_reports_added_file(tmp_path: Path) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    (tmp_path / "installed" / "code-review" / "notes.md").write_text(
        "notes",
        encoding="utf-8",
    )

    comparison = FilesystemSkillDirectoryAdapter().compare(entry, workspace)

    assert comparison.status is SkillChangeStatus.CHANGED
    assert comparison.changed_file_count == 1


def test_skill_directory_adapter_rejects_missing_installed_target(
    tmp_path: Path,
) -> None:
    _, workspace = arrange_skill_directories(tmp_path)
    missing_entry = contribution_lockfile_entry(target=str(tmp_path / "missing"))

    with pytest.raises(
        MissingInstalledSkillTargetError,
        match="installed skill target",
    ):
        FilesystemSkillDirectoryAdapter().compare(missing_entry, workspace)


@pytest.mark.parametrize(
    "skill_path",
    ["../code-review", "/code-review", "code-review/", "code-review//nested"],
)
def test_skill_directory_adapter_rejects_unsafe_skill_path(
    tmp_path: Path,
    skill_path: str,
) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    unsafe_entry = unsafe_contribution_entry(
        target=entry.target,
        skill_path=skill_path,
        skill_file="code-review/SKILL.md",
    )

    with pytest.raises(UnsafeContributionPathError, match="skill_path"):
        FilesystemSkillDirectoryAdapter().compare(unsafe_entry, workspace)


def test_skill_directory_adapter_rejects_skill_file_outside_skill_path(
    tmp_path: Path,
) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    unsafe_entry = contribution_lockfile_entry(
        target=entry.target,
        skill_file="other/SKILL.md",
    )

    with pytest.raises(UnsafeContributionPathError, match="inside skill_path"):
        FilesystemSkillDirectoryAdapter().compare(unsafe_entry, workspace)


def test_skill_directory_adapter_rejects_missing_source_skill_directory(
    tmp_path: Path,
) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    source_skill = tmp_path / "checkout" / "skills" / "code-review"
    remove_tree(source_skill)

    with pytest.raises(SkillContributionError, match="source skill directory"):
        FilesystemSkillDirectoryAdapter().compare(entry, workspace)


def test_skill_directory_adapter_rejects_missing_source_skill_file(
    tmp_path: Path,
) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    (tmp_path / "checkout" / "skills" / "code-review" / "SKILL.md").unlink()

    with pytest.raises(SkillContributionError, match=r"missing SKILL\.md"):
        FilesystemSkillDirectoryAdapter().compare(entry, workspace)


def test_skill_directory_adapter_rejects_installed_symlink(tmp_path: Path) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    (tmp_path / "installed" / "code-review" / "linked").symlink_to(
        tmp_path / "outside.txt",
    )

    with pytest.raises(UnsafeContributionPathError, match="symlink"):
        FilesystemSkillDirectoryAdapter().compare(entry, workspace)


def test_skill_directory_adapter_rejects_source_symlink(tmp_path: Path) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    (tmp_path / "checkout" / "skills" / "code-review" / "linked").symlink_to(
        tmp_path / "outside.txt",
    )

    with pytest.raises(UnsafeContributionPathError, match="symlink"):
        FilesystemSkillDirectoryAdapter().compare(entry, workspace)


def test_skill_directory_adapter_copies_installed_skill_into_checkout(
    tmp_path: Path,
) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    installed = tmp_path / "installed" / "code-review"
    source = tmp_path / "checkout" / "skills" / "code-review"
    sibling = tmp_path / "checkout" / "skills" / "security-review"
    sibling.mkdir()
    (sibling / "SKILL.md").write_text("sibling", encoding="utf-8")
    (installed / "SKILL.md").write_text("changed", encoding="utf-8")
    (installed / "docs.md").write_text("docs", encoding="utf-8")
    (source / "old.md").write_text("old", encoding="utf-8")

    FilesystemSkillDirectoryAdapter().copy_installed_skill(entry, workspace)

    assert (source / "SKILL.md").read_text(encoding="utf-8") == "changed"
    assert (source / "docs.md").read_text(encoding="utf-8") == "docs"
    assert not (source / "old.md").exists()
    assert (sibling / "SKILL.md").read_text(encoding="utf-8") == "sibling"


def test_skill_directory_adapter_rejects_destination_parent_symlink(
    tmp_path: Path,
) -> None:
    entry, workspace = arrange_skill_directories(tmp_path)
    remove_tree(tmp_path / "checkout" / "skills")
    (tmp_path / "checkout" / "real-skills").mkdir()
    (tmp_path / "checkout" / "skills").symlink_to(tmp_path / "checkout" / "real-skills")

    with pytest.raises(UnsafeContributionPathError, match=r"escapes|symlink"):
        FilesystemSkillDirectoryAdapter().copy_installed_skill(entry, workspace)


def arrange_skill_directories(
    tmp_path: Path,
) -> tuple[ContributionLockfileEntry, ContributionWorkspace]:
    installed = tmp_path / "installed" / "code-review"
    source = tmp_path / "checkout" / "skills" / "code-review"
    installed.mkdir(parents=True)
    source.mkdir(parents=True)
    (installed / "SKILL.md").write_text("name: code-review", encoding="utf-8")
    (source / "SKILL.md").write_text("name: code-review", encoding="utf-8")
    entry = contribution_lockfile_entry(
        target=str(installed),
        skill_path="skills/code-review",
        skill_file="skills/code-review/SKILL.md",
    )
    workspace = ContributionWorkspace(
        checkout_path=str(tmp_path / "checkout"),
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )
    return entry, workspace


def contribution_lockfile_entry(
    *,
    target: str,
    skill_path: str = "skills/code-review",
    skill_file: str = "skills/code-review/SKILL.md",
) -> ContributionLockfileEntry:
    return ContributionLockfileEntry(
        requirement="platform-skills/code-review",
        index_name="platform-skills",
        skill_name="code-review",
        target=target,
        source="git@example.com:example/skills.git",
        source_type="git_url",
        source_revision="abc123",
        skill_path=skill_path,
        skill_file=skill_file,
        index_schema_version=1,
    )


@dataclass(frozen=True)
class UnsafeContributionEntry:
    requirement: str
    index_name: str
    skill_name: str
    target: str
    source: str
    source_type: str
    source_revision: str
    skill_path: str
    skill_file: str
    index_schema_version: int


def unsafe_contribution_entry(
    *,
    target: str,
    skill_path: str,
    skill_file: str,
) -> ContributionLockfileEntry:
    return cast(
        "ContributionLockfileEntry",
        UnsafeContributionEntry(
            requirement="platform-skills/code-review",
            index_name="platform-skills",
            skill_name="code-review",
            target=target,
            source="git@example.com:example/skills.git",
            source_type="git_url",
            source_revision="abc123",
            skill_path=skill_path,
            skill_file=skill_file,
            index_schema_version=1,
        ),
    )


def remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
