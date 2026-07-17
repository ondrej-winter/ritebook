from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound import (
    filesystem_installer,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    ResolvedSkillSource,
)
from ritebook.features.skill_installation.application.errors import (
    ExistingInstallTargetError,
    UnsafeInstallPathError,
)

FilesystemSkillInstallerAdapter = filesystem_installer.FilesystemSkillInstallerAdapter


def test_filesystem_installer_copies_directory_recursively_and_creates_parents(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill_dir = repository / "skills" / "code-review"
    nested_dir = skill_dir / "assets"
    nested_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Code review\n", encoding="utf-8")
    (nested_dir / "checklist.md").write_text("- Check tests\n", encoding="utf-8")

    target = tmp_path / "target" / "skills" / "code-review"

    FilesystemSkillInstallerAdapter().install(
        source=resolved_source(repository),
        skill=installable_skill(),
        target=str(target),
        force=False,
    )

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# Code review\n"
    assert (target / "assets" / "checklist.md").read_text(encoding="utf-8") == (
        "- Check tests\n"
    )


def test_filesystem_installer_resolves_skills_below_published_source_root(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill_dir = repository / "skills" / "software-development" / "code-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Code review\n", encoding="utf-8")
    target = tmp_path / "target" / "code-review"

    FilesystemSkillInstallerAdapter().install(
        source=resolved_source(repository),
        skill=installable_skill(
            path="software-development/code-review",
            skill_file="software-development/code-review/SKILL.md",
            source_root="skills",
        ),
        target=str(target),
        force=False,
    )

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# Code review\n"


def test_filesystem_installer_refuses_existing_target_without_force(
    tmp_path: Path,
) -> None:
    repository = repository_with_skill(tmp_path)
    target = tmp_path / "target" / "code-review"
    target.mkdir(parents=True)

    with pytest.raises(ExistingInstallTargetError, match="already exists"):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=str(target),
            force=False,
        )

    assert target.is_dir()


def test_filesystem_installer_replaces_only_target_with_force(tmp_path: Path) -> None:
    repository = repository_with_skill(tmp_path)
    target_parent = tmp_path / "target"
    target = target_parent / "code-review"
    target.mkdir(parents=True)
    (target / "old.md").write_text("old", encoding="utf-8")
    sibling = target_parent / "keep.md"
    sibling.write_text("keep", encoding="utf-8")

    FilesystemSkillInstallerAdapter().install(
        source=resolved_source(repository),
        skill=installable_skill(),
        target=str(target),
        force=True,
    )

    assert not (target / "old.md").exists()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# Code review\n"
    assert sibling.read_text(encoding="utf-8") == "keep"


def test_filesystem_installer_replaces_existing_file_target_with_force(
    tmp_path: Path,
) -> None:
    repository = repository_with_skill(tmp_path)
    target_parent = tmp_path / "target"
    target = target_parent / "code-review"
    target_parent.mkdir()
    target.write_text("old", encoding="utf-8")
    sibling = target_parent / "keep.md"
    sibling.write_text("keep", encoding="utf-8")

    FilesystemSkillInstallerAdapter().install(
        source=resolved_source(repository),
        skill=installable_skill(),
        target=str(target),
        force=True,
    )

    assert target.is_dir()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# Code review\n"
    assert sibling.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize(
    ("skill_path", "skill_file"),
    [
        ("/skills/code-review", "skills/code-review/SKILL.md"),
        ("../code-review", "../code-review/SKILL.md"),
        ("skills\\code-review", "skills/code-review/SKILL.md"),
        ("skills/code-review", "/skills/code-review/SKILL.md"),
        ("skills/code-review", "skills/../SKILL.md"),
        ("skills/code-review", "skills\\code-review\\SKILL.md"),
        ("skills/code-review", "other/SKILL.md"),
    ],
)
def test_filesystem_installer_rejects_unsafe_source_metadata(
    tmp_path: Path,
    skill_path: str,
    skill_file: str,
) -> None:
    repository = repository_with_skill(tmp_path)

    with pytest.raises(UnsafeInstallPathError):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(path=skill_path, skill_file=skill_file),
            target=str(tmp_path / "target" / "code-review"),
            force=False,
        )


@pytest.mark.parametrize("target", ["/", "~"])
def test_filesystem_installer_rejects_broad_absolute_targets(
    tmp_path: Path,
    target: str,
) -> None:
    repository = repository_with_skill(tmp_path)

    with pytest.raises(UnsafeInstallPathError):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=target,
            force=True,
        )


def test_filesystem_installer_rejects_current_working_directory_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = repository_with_skill(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(UnsafeInstallPathError, match="current working directory"):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=".",
            force=True,
        )


def test_filesystem_installer_rejects_existing_symlink_target(tmp_path: Path) -> None:
    repository = repository_with_skill(tmp_path)
    symlink_target = tmp_path / "target-link"
    symlink_target.symlink_to(tmp_path / "actual-target")

    with pytest.raises(UnsafeInstallPathError, match="symlink"):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=str(symlink_target),
            force=True,
        )


def test_filesystem_installer_rejects_symlink_source_directory(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    actual_skill = tmp_path / "outside-skill"
    actual_skill.mkdir()
    (actual_skill / "SKILL.md").write_text("# Outside\n", encoding="utf-8")
    (repository / "skills").mkdir(parents=True)
    (repository / "skills" / "code-review").symlink_to(
        actual_skill,
        target_is_directory=True,
    )

    with pytest.raises(UnsafeInstallPathError, match="symlink"):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=str(tmp_path / "target" / "code-review"),
            force=False,
        )


def test_filesystem_installer_rejects_symlink_skill_file(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    skill_dir = repository / "skills" / "code-review"
    skill_dir.mkdir(parents=True)
    actual_skill_file = tmp_path / "outside-SKILL.md"
    actual_skill_file.write_text("# Outside\n", encoding="utf-8")
    (skill_dir / "SKILL.md").symlink_to(actual_skill_file)

    with pytest.raises(UnsafeInstallPathError, match="symlink"):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=str(tmp_path / "target" / "code-review"),
            force=False,
        )


def test_filesystem_installer_rejects_symlink_inside_source_directory(
    tmp_path: Path,
) -> None:
    repository = repository_with_skill(tmp_path)
    outside_asset = tmp_path / "outside-asset.md"
    outside_asset.write_text("outside", encoding="utf-8")
    (repository / "skills" / "code-review" / "asset-link.md").symlink_to(
        outside_asset,
    )

    with pytest.raises(UnsafeInstallPathError, match="contains symlinks"):
        FilesystemSkillInstallerAdapter().install(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=str(tmp_path / "target" / "code-review"),
            force=False,
        )


def repository_with_skill(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    skill_dir = repository / "skills" / "code-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Code review\n", encoding="utf-8")
    return repository


def resolved_source(repository_path: Path) -> ResolvedSkillSource:
    return ResolvedSkillSource(
        source="git@example.com:company/skills.git",
        source_type="git_url",
        repository_path=str(repository_path),
        source_revision="abc123",
    )


def installable_skill(
    *,
    path: str = "skills/code-review",
    skill_file: str = "skills/code-review/SKILL.md",
    source_root: str = ".",
) -> InstallableSkill:
    return InstallableSkill(
        name="code-review",
        path=path,
        skill_file=skill_file,
        source_root=source_root,
    )
