import os
import stat
from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound import (
    FilesystemSkillInstallerAdapter,
    filesystem_installer,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    ResolvedSkillSource,
)
from ritebook.features.skill_installation.application.errors import (
    InstallationPersistenceError,
    UnsafeInstallPathError,
)


def test_filesystem_installer_plans_canonical_target_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    planned = FilesystemSkillInstallerAdapter().plan_target(
        "targets/nested/../code-review",
    )

    assert planned.requested_target == "targets/nested/../code-review"
    assert planned.canonical_target == str(
        (tmp_path / "targets" / "code-review").resolve(strict=False),
    )
    assert not (tmp_path / "targets").exists()


@pytest.mark.parametrize("target", ["/", "~"])
def test_filesystem_installer_rejects_broad_absolute_targets(target: str) -> None:
    with pytest.raises(UnsafeInstallPathError):
        FilesystemSkillInstallerAdapter().plan_target(target)


def test_filesystem_installer_rejects_current_working_directory_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(UnsafeInstallPathError, match="current working directory"):
        FilesystemSkillInstallerAdapter().plan_target(".")


def test_filesystem_installer_rejects_symlinked_target_ancestor_during_planning(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    target_root = tmp_path / "targets"
    target_root.mkdir()
    (target_root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeInstallPathError, match="symlink"):
        FilesystemSkillInstallerAdapter().plan_target(
            str(target_root / "linked" / "code-review"),
        )

    assert list(outside.iterdir()) == []


def test_filesystem_installer_inspects_missing_directory_and_file_targets(
    tmp_path: Path,
) -> None:
    adapter = FilesystemSkillInstallerAdapter()
    missing = adapter.plan_target(str(tmp_path / "missing"))
    existing_directory = tmp_path / "directory"
    existing_directory.mkdir()
    (existing_directory / "SKILL.md").write_text("skill\n", encoding="utf-8")
    existing_file = tmp_path / "file"
    existing_file.write_text("not a tree\n", encoding="utf-8")

    missing_result = adapter.inspect_target(missing)
    directory_result = adapter.inspect_target(
        adapter.plan_target(str(existing_directory)),
    )
    file_result = adapter.inspect_target(adapter.plan_target(str(existing_file)))

    assert missing_result.exists is False
    assert missing_result.installed_tree_digest is None
    assert directory_result.exists is True
    assert directory_result.installed_tree_digest == adapter.tree_digest(
        str(existing_directory),
    )
    assert file_result.exists is True
    assert file_result.installed_tree_digest is None


def test_filesystem_installer_rejects_symlink_target_during_inspection(
    tmp_path: Path,
) -> None:
    actual_target = tmp_path / "actual-target"
    actual_target.mkdir()
    symlink_target = tmp_path / "target-link"
    symlink_target.symlink_to(actual_target, target_is_directory=True)
    adapter = FilesystemSkillInstallerAdapter()

    with pytest.raises(UnsafeInstallPathError, match="symlink"):
        adapter.inspect_target(
            adapter.plan_target(str(symlink_target.parent / "missing")).__class__(
                requested_target=str(symlink_target),
                canonical_target=str(symlink_target),
            ),
        )


def test_filesystem_installer_stages_directory_recursively_beside_target(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill_directory = repository / "skills" / "code-review"
    (skill_directory / "assets").mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text("# Code review\n", encoding="utf-8")
    (skill_directory / "assets" / "checklist.md").write_text(
        "- Check tests\n",
        encoding="utf-8",
    )
    target = tmp_path / "targets" / "nested" / "code-review"
    adapter = FilesystemSkillInstallerAdapter()

    staged = adapter.stage(
        source=resolved_source(repository),
        skill=installable_skill(),
        target=adapter.plan_target(str(target)),
    )

    staged_path = Path(staged.staged_path)
    cleanup_path = Path(staged.cleanup_path)
    assert cleanup_path.parent == target.parent
    assert staged_path.parent == cleanup_path
    assert (staged_path / "SKILL.md").read_text(encoding="utf-8") == ("# Code review\n")
    assert (staged_path / "assets" / "checklist.md").read_text(
        encoding="utf-8",
    ) == "- Check tests\n"
    assert staged.installed_tree_digest == adapter.tree_digest(str(staged_path))

    adapter.cleanup_staged(staged)

    assert not cleanup_path.exists()


def test_filesystem_installer_resolves_skill_below_published_source_root(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill_directory = repository / "skills" / "software-development" / "code-review"
    skill_directory.mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text("# Code review\n", encoding="utf-8")
    adapter = FilesystemSkillInstallerAdapter()

    staged = adapter.stage(
        source=resolved_source(repository),
        skill=installable_skill(
            path="software-development/code-review",
            skill_file="software-development/code-review/SKILL.md",
            source_root="skills",
        ),
        target=adapter.plan_target(str(tmp_path / "target" / "code-review")),
    )
    try:
        assert Path(staged.staged_path, "SKILL.md").read_text(encoding="utf-8") == (
            "# Code review\n"
        )
    finally:
        adapter.cleanup_staged(staged)


def test_filesystem_installer_stage_failure_removes_partial_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = repository_with_skill(tmp_path)
    target_parent = tmp_path / "targets"
    target = target_parent / "code-review"

    def fail_copy(*_args: object, **_kwargs: object) -> None:
        message = "injected stage failure"
        raise OSError(message)

    monkeypatch.setattr(filesystem_installer.adapter, "_copy_directory", fail_copy)

    with pytest.raises(InstallationPersistenceError, match="stage replacement"):
        FilesystemSkillInstallerAdapter().stage(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=FilesystemSkillInstallerAdapter().plan_target(str(target)),
        )

    assert target_parent.is_dir()
    assert list(target_parent.iterdir()) == []


def test_filesystem_installer_stage_rejects_symlink_ancestor_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = repository_with_skill(tmp_path)
    target_root = tmp_path / "targets"
    target_parent = target_root / "skills"
    target_parent.mkdir(parents=True)
    displaced_root = tmp_path / "displaced-targets"
    outside = tmp_path / "outside"
    outside.mkdir()
    adapter = FilesystemSkillInstallerAdapter()
    planned = adapter.plan_target(str(target_parent / "code-review"))
    require_no_overlap = (
        filesystem_installer.adapter._require_no_source_target_overlap  # noqa: SLF001
    )

    def replace_ancestor_after_validation(
        source_directory: Path,
        target_path: Path,
    ) -> None:
        require_no_overlap(source_directory, target_path)
        target_root.rename(displaced_root)
        target_root.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(
        filesystem_installer.adapter,
        "_require_no_source_target_overlap",
        replace_ancestor_after_validation,
    )

    with pytest.raises(UnsafeInstallPathError, match=r"symlink|safely"):
        adapter.stage(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=planned,
        )

    assert list(outside.iterdir()) == []
    assert list(displaced_root.joinpath("skills").iterdir()) == []


def test_filesystem_installer_cleanup_rejects_symlink_ancestor_race(
    tmp_path: Path,
) -> None:
    repository = repository_with_skill(tmp_path)
    target_root = tmp_path / "targets"
    target_parent = target_root / "skills"
    adapter = FilesystemSkillInstallerAdapter()
    staged = adapter.stage(
        source=resolved_source(repository),
        skill=installable_skill(),
        target=adapter.plan_target(str(target_parent / "code-review")),
    )
    cleanup_path = Path(staged.cleanup_path)
    displaced_root = tmp_path / "displaced-targets"
    outside = tmp_path / "outside"
    outside_cleanup = outside / "skills" / cleanup_path.name
    outside_cleanup.mkdir(parents=True)
    sentinel = outside_cleanup / "sentinel.txt"
    sentinel.write_text("outside\n", encoding="utf-8")
    target_root.rename(displaced_root)
    target_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(InstallationPersistenceError, match="staged skill data"):
        adapter.cleanup_staged(staged)

    assert sentinel.read_text(encoding="utf-8") == "outside\n"
    retained_staged = displaced_root / "skills" / cleanup_path.name / "candidate"
    assert (retained_staged / "SKILL.md").read_text(encoding="utf-8") == (
        "# Code review\n"
    )


@pytest.mark.parametrize("relationship", ["equal", "ancestor", "descendant"])
def test_filesystem_installer_rejects_source_target_overlap_before_staging(
    tmp_path: Path,
    relationship: str,
) -> None:
    repository = repository_with_skill(tmp_path)
    source_directory = repository / "skills" / "code-review"
    if relationship == "equal":
        target = source_directory
    elif relationship == "ancestor":
        target = repository / "skills"
    else:
        target = source_directory / "installed-copy"
    adapter = FilesystemSkillInstallerAdapter()

    with pytest.raises(UnsafeInstallPathError, match="source-target overlap"):
        adapter.stage(
            source=resolved_source(repository),
            skill=installable_skill(),
            target=adapter.plan_target(str(target)),
        )

    assert (source_directory / "SKILL.md").read_text(encoding="utf-8") == (
        "# Code review\n"
    )
    assert not (source_directory / "installed-copy").exists()


def test_filesystem_installer_allows_safe_sibling_of_source_directory(
    tmp_path: Path,
) -> None:
    repository = repository_with_skill(tmp_path)
    adapter = FilesystemSkillInstallerAdapter()
    target = repository / "skills" / "installed-code-review"

    staged = adapter.stage(
        source=resolved_source(repository),
        skill=installable_skill(),
        target=adapter.plan_target(str(target)),
    )
    try:
        assert Path(staged.staged_path, "SKILL.md").read_text(encoding="utf-8") == (
            "# Code review\n"
        )
    finally:
        adapter.cleanup_staged(staged)


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
    adapter = FilesystemSkillInstallerAdapter()

    with pytest.raises(UnsafeInstallPathError):
        adapter.stage(
            source=resolved_source(repository),
            skill=installable_skill(path=skill_path, skill_file=skill_file),
            target=adapter.plan_target(str(tmp_path / "target" / "code-review")),
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
        stage_default_skill(repository, tmp_path / "target" / "code-review")


def test_filesystem_installer_rejects_symlink_skill_file(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    skill_directory = repository / "skills" / "code-review"
    skill_directory.mkdir(parents=True)
    actual_skill_file = tmp_path / "outside-SKILL.md"
    actual_skill_file.write_text("# Outside\n", encoding="utf-8")
    (skill_directory / "SKILL.md").symlink_to(actual_skill_file)

    with pytest.raises(UnsafeInstallPathError, match="symlink"):
        stage_default_skill(repository, tmp_path / "target" / "code-review")


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
        stage_default_skill(repository, tmp_path / "target" / "code-review")


def test_filesystem_installer_tree_digest_is_stable_across_creation_order_and_mtime(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    (first / "assets").mkdir(parents=True)
    (first / "SKILL.md").write_bytes(b"skill\n")
    (first / "assets" / "guide.md").write_bytes(b"guide\n")
    (second / "assets").mkdir(parents=True)
    (second / "assets" / "guide.md").write_bytes(b"guide\n")
    (second / "SKILL.md").write_bytes(b"skill\n")
    (second / "SKILL.md").touch()
    adapter = FilesystemSkillInstallerAdapter()

    assert adapter.tree_digest(str(first)) == adapter.tree_digest(str(second))


def test_filesystem_installer_tree_digest_changes_with_content_path_and_executable_bit(
    tmp_path: Path,
) -> None:
    tree = tmp_path / "skill"
    tree.mkdir()
    skill_file = tree / "SKILL.md"
    skill_file.write_bytes(b"first\n")
    adapter = FilesystemSkillInstallerAdapter()
    original = adapter.tree_digest(str(tree))

    skill_file.write_bytes(b"second\n")
    content_changed = adapter.tree_digest(str(tree))
    skill_file.write_bytes(b"first\n")
    skill_file.chmod(skill_file.stat().st_mode | stat.S_IXUSR)
    executable_changed = adapter.tree_digest(str(tree))
    skill_file.chmod(skill_file.stat().st_mode & ~stat.S_IXUSR)
    skill_file.rename(tree / "GUIDE.md")
    path_changed = adapter.tree_digest(str(tree))

    assert len({original, content_changed, executable_changed, path_changed}) == 4


@pytest.mark.parametrize("entry_kind", ["symlink", "fifo"])
def test_filesystem_installer_tree_digest_rejects_non_regular_entries(
    tmp_path: Path,
    entry_kind: str,
) -> None:
    tree = tmp_path / "skill"
    tree.mkdir()
    (tree / "SKILL.md").write_text("skill\n", encoding="utf-8")
    unsafe_entry = tree / "unsafe"
    if entry_kind == "symlink":
        unsafe_entry.symlink_to(tree / "SKILL.md")
    else:
        os.mkfifo(unsafe_entry)

    with pytest.raises(UnsafeInstallPathError, match="regular files and directories"):
        FilesystemSkillInstallerAdapter().tree_digest(str(tree))


def test_filesystem_installer_tree_digest_rejects_symlinked_ancestor(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    tree = outside / "skill"
    tree.mkdir(parents=True)
    (tree / "SKILL.md").write_text("skill\n", encoding="utf-8")
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeInstallPathError, match="readable directory"):
        FilesystemSkillInstallerAdapter().tree_digest(str(linked_root / "skill"))


def repository_with_skill(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    skill_directory = repository / "skills" / "code-review"
    skill_directory.mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text("# Code review\n", encoding="utf-8")
    return repository


def resolved_source(repository_path: Path) -> ResolvedSkillSource:
    return ResolvedSkillSource(
        source="git@example.com:company/skills.git",
        source_type="git_url",
        repository_path=str(repository_path),
        source_revision="a" * 40,
        source_branch="refs/heads/main",
        index_digest=f"sha256:{'b' * 64}",
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
        description="Helps review code.",
        source_root=source_root,
    )


def stage_default_skill(repository: Path, target: Path) -> None:
    adapter = FilesystemSkillInstallerAdapter()
    adapter.stage(
        source=resolved_source(repository),
        skill=installable_skill(),
        target=adapter.plan_target(str(target)),
    )
