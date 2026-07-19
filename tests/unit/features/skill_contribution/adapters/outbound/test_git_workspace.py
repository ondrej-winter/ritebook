import hashlib
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import cast

import pytest

from ritebook.features.skill_contribution.adapters.outbound.git_workspace import (
    GitSkillChangeDetectorAdapter,
    GitWorkspaceAdapter,
)
from ritebook.features.skill_contribution.adapters.outbound.git_workspace import (
    adapter as git_workspace_adapter,
)
from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
    SkillChangeComparison,
    SkillChangeStatus,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionGitError,
    IncompleteContributionProvenanceError,
)


class RecordingRunner:
    def __init__(
        self,
        responses: dict[tuple[str, ...], tuple[int, str, str]] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        recorded = list(command)
        self.commands.append(recorded)
        if "clone" in recorded:
            Path(recorded[-1], ".git").mkdir(parents=True, exist_ok=True)
        returncode, stdout, stderr = self.responses.get(tuple(recorded), (0, "", ""))
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)


class RecordingLocalChangeDetector:
    def __init__(self, comparison: SkillChangeComparison) -> None:
        self.comparison = comparison
        self.calls: list[tuple[ContributionLockfileEntry, ContributionWorkspace]] = []

    def compare(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> SkillChangeComparison:
        self.calls.append((entry, workspace))
        return self.comparison


def test_git_change_detector_delegates_when_selected_upstream_path_is_unchanged() -> (
    None
):
    entry = contribution_entry()
    workspace = contribution_workspace()
    diff_command = git(
        Path(workspace.checkout_path),
        "diff",
        "--quiet",
        entry.source_revision,
        workspace.current_base_revision,
        "--",
        entry.skill_path,
    )
    runner = RecordingRunner({diff_command: (0, "", "")})
    local_comparison = SkillChangeComparison(
        status=SkillChangeStatus.CHANGED,
        installed_path=entry.target,
        source_skill_path=entry.skill_path,
        changed_file_count=2,
    )
    local_detector = RecordingLocalChangeDetector(local_comparison)

    comparison = GitSkillChangeDetectorAdapter(
        local_change_detector=local_detector,
        runner=runner,
    ).compare(entry, workspace)

    assert comparison == local_comparison
    assert local_detector.calls == [(entry, workspace)]
    assert runner.commands == [list(diff_command)]


def test_git_change_detector_reports_changed_selected_upstream_path() -> None:
    entry = contribution_entry(skill_path="skills/code-review")
    workspace = contribution_workspace()
    diff_command = git(
        Path(workspace.checkout_path),
        "diff",
        "--quiet",
        entry.source_revision,
        workspace.current_base_revision,
        "--",
        entry.skill_path,
    )
    runner = RecordingRunner({diff_command: (1, "", "")})
    local_detector = RecordingLocalChangeDetector(
        SkillChangeComparison(
            status=SkillChangeStatus.NO_CHANGES,
            installed_path=entry.target,
            source_skill_path=entry.skill_path,
        ),
    )

    comparison = GitSkillChangeDetectorAdapter(
        local_change_detector=local_detector,
        runner=runner,
    ).compare(entry, workspace)

    assert comparison == SkillChangeComparison(
        status=SkillChangeStatus.UPSTREAM_CHANGED,
        installed_path=entry.target,
        source_skill_path=entry.skill_path,
        changed_file_count=1,
    )
    assert local_detector.calls == []
    assert runner.commands == [list(diff_command)]


def test_git_change_detector_rejects_missing_locked_revision() -> None:
    entry = contribution_entry()
    incomplete_entry = cast(
        "ContributionLockfileEntry",
        IncompleteContributionEntry(
            requirement=entry.requirement,
            target=entry.target,
            source_revision="",
            skill_path=entry.skill_path,
        ),
    )
    runner = RecordingRunner()
    local_detector = RecordingLocalChangeDetector(
        SkillChangeComparison(
            status=SkillChangeStatus.NO_CHANGES,
            installed_path=entry.target,
            source_skill_path=entry.skill_path,
        ),
    )

    with pytest.raises(
        IncompleteContributionProvenanceError,
        match="source_revision",
    ):
        GitSkillChangeDetectorAdapter(
            local_change_detector=local_detector,
            runner=runner,
        ).compare(incomplete_entry, contribution_workspace())

    assert runner.commands == []
    assert local_detector.calls == []


def test_git_change_detector_sanitizes_git_failure_output() -> None:
    entry = contribution_entry()
    workspace = contribution_workspace()
    diff_command = git(
        Path(workspace.checkout_path),
        "diff",
        "--quiet",
        entry.source_revision,
        workspace.current_base_revision,
        "--",
        entry.skill_path,
    )
    runner = RecordingRunner(
        {diff_command: (128, "", "fatal: https://secret@example.com failed")},
    )
    local_detector = RecordingLocalChangeDetector(
        SkillChangeComparison(
            status=SkillChangeStatus.NO_CHANGES,
            installed_path=entry.target,
            source_skill_path=entry.skill_path,
        ),
    )

    with pytest.raises(ContributionGitError) as exc_info:
        GitSkillChangeDetectorAdapter(
            local_change_detector=local_detector,
            runner=runner,
        ).compare(entry, workspace)

    assert str(exc_info.value) == "git upstream skill-path inspection failed"
    assert "secret" not in str(exc_info.value)
    assert "example.com" not in str(exc_info.value)
    assert local_detector.calls == []


@dataclass(frozen=True)
class IncompleteContributionEntry:
    requirement: str
    target: str
    source_revision: str
    skill_path: str


def test_git_workspace_clones_git_url_to_deterministic_owned_path(
    tmp_path: Path,
) -> None:
    contribution_root = tmp_path / "contributions"
    entry = contribution_entry()
    checkout_path = expected_checkout_path(contribution_root, entry)
    runner = RecordingRunner(
        {
            git(checkout_path, "remote", "get-url", "origin"): (
                0,
                "git@example.com:example/skills.git\n",
                "",
            ),
            git(
                checkout_path,
                "symbolic-ref",
                "--quiet",
                "--short",
                "refs/remotes/origin/HEAD",
            ): (0, "origin/main\n", ""),
            git(checkout_path, "rev-parse", "HEAD"): (0, "def456\n", ""),
        },
    )

    workspace = GitWorkspaceAdapter(
        runner=runner,
        default_contribution_root=lambda: tmp_path / "unused-default",
    ).prepare_workspace(entry, str(contribution_root))

    assert Path(workspace.checkout_path) == checkout_path
    assert workspace.current_base_revision == "def456"
    assert workspace.locked_revision == "abc123"
    assert workspace.source_skill_path == "skills/code-review"
    assert workspace.has_usable_origin is True
    assert entry.source not in workspace.checkout_path
    assert runner.commands == [
        ["git", "--no-pager", "clone", "--", entry.source, str(checkout_path)],
        ["git", "--no-pager", "-C", str(checkout_path), "remote", "get-url", "origin"],
        ["git", "--no-pager", "-C", str(checkout_path), "fetch", "--prune", "origin"],
        [
            "git",
            "--no-pager",
            "-C",
            str(checkout_path),
            "symbolic-ref",
            "--quiet",
            "--short",
            "refs/remotes/origin/HEAD",
        ],
        [
            "git",
            "--no-pager",
            "-C",
            str(checkout_path),
            "checkout",
            "--detach",
            "origin/main",
        ],
        [
            "git",
            "--no-pager",
            "-C",
            str(checkout_path),
            "reset",
            "--hard",
            "origin/main",
        ],
        ["git", "--no-pager", "-C", str(checkout_path), "clean", "-fd"],
        ["git", "--no-pager", "-C", str(checkout_path), "rev-parse", "HEAD"],
    ]


def test_git_workspace_reuses_owned_checkout_without_cloning(tmp_path: Path) -> None:
    contribution_root = tmp_path / "contributions"
    entry = contribution_entry()
    checkout_path = expected_checkout_path(contribution_root, entry)
    write_workspace_marker(checkout_path)
    runner = RecordingRunner(
        {
            git(checkout_path, "remote", "get-url", "origin"): (
                0,
                "git@example.com:example/skills.git\n",
                "",
            ),
            git(
                checkout_path,
                "symbolic-ref",
                "--quiet",
                "--short",
                "refs/remotes/origin/HEAD",
            ): (0, "origin/main\n", ""),
            git(checkout_path, "rev-parse", "HEAD"): (0, "def456\n", ""),
        },
    )

    GitWorkspaceAdapter(runner=runner).prepare_workspace(
        entry,
        str(contribution_root),
    )

    assert all("clone" not in command for command in runner.commands)
    assert git(checkout_path, "reset", "--hard", "origin/main") in [
        tuple(command) for command in runner.commands
    ]
    assert git(checkout_path, "clean", "-fd") in [
        tuple(command) for command in runner.commands
    ]


def test_git_workspace_paths_do_not_collide_for_flattened_skill_slugs(
    tmp_path: Path,
) -> None:
    first = contribution_entry(
        requirement="platform-skills/a/b-c",
        skill_name="b-c",
        skill_path="a/b-c",
    )
    second = contribution_entry(
        requirement="platform-skills/a-b/c",
        skill_name="c",
        skill_path="a-b/c",
    )

    first_path = expected_checkout_path(tmp_path, first)
    second_path = expected_checkout_path(tmp_path, second)

    assert first_path != second_path
    assert first_path.name.startswith("platform-skills-a-b-c-")
    assert second_path.name.startswith("platform-skills-a-b-c-")


def test_git_workspace_rejects_symlinked_checkout_before_git_cleanup(
    tmp_path: Path,
) -> None:
    entry = contribution_entry()
    checkout_path = expected_checkout_path(tmp_path, entry)
    user_repository = tmp_path / "user-repository"
    user_repository.mkdir()
    user_file = user_repository / "keep.txt"
    user_file.write_text("keep me\n", encoding="utf-8")
    checkout_path.parent.mkdir(parents=True)
    checkout_path.symlink_to(user_repository, target_is_directory=True)
    runner = RecordingRunner()

    with pytest.raises(ContributionGitError, match="contains a symlink"):
        GitWorkspaceAdapter(runner=runner).prepare_workspace(entry, str(tmp_path))

    assert runner.commands == []
    assert user_file.read_text(encoding="utf-8") == "keep me\n"


def test_git_workspace_rejects_unmarked_git_checkout_before_cleanup(
    tmp_path: Path,
) -> None:
    entry = contribution_entry()
    checkout_path = expected_checkout_path(tmp_path, entry)
    (checkout_path / ".git").mkdir(parents=True)
    user_file = checkout_path / "keep.txt"
    user_file.write_text("keep me\n", encoding="utf-8")
    runner = RecordingRunner()

    with pytest.raises(
        ContributionGitError,
        match="not a reusable Ritebook-owned clone",
    ):
        GitWorkspaceAdapter(runner=runner).prepare_workspace(entry, str(tmp_path))

    assert runner.commands == []
    assert user_file.read_text(encoding="utf-8") == "keep me\n"


def test_git_workspace_uses_injected_default_contribution_root(
    tmp_path: Path,
) -> None:
    default_root = tmp_path / "isolated-default"
    entry = contribution_entry()
    checkout_path = expected_checkout_path(default_root, entry)
    runner = RecordingRunner(
        {
            git(checkout_path, "remote", "get-url", "origin"): (1, "", "missing"),
            git(checkout_path, "rev-parse", "HEAD"): (0, "def456\n", ""),
        },
    )

    workspace = GitWorkspaceAdapter(
        runner=runner,
        default_contribution_root=lambda: default_root,
    ).prepare_workspace(entry, None)

    assert Path(workspace.checkout_path).is_relative_to(default_root)
    assert workspace.has_usable_origin is False
    assert all("fetch" not in command for command in runner.commands)


def test_git_workspace_local_clone_does_not_mutate_user_working_tree(
    tmp_path: Path,
) -> None:
    if which("git") is None:
        pytest.skip("git executable is required")
    source = tmp_path / "user-source"
    source.mkdir()
    run_git(source, "init", "--initial-branch", "main")
    run_git(source, "config", "user.name", "Ritebook Test")
    run_git(source, "config", "user.email", "ritebook@example.invalid")
    skill_file = source / "skills" / "code-review" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("# original\n", encoding="utf-8")
    run_git(source, "add", ".")
    run_git(source, "commit", "--message", "Initial skill")
    untracked = source / "local-notes.txt"
    untracked.write_text("keep me\n", encoding="utf-8")
    status_before = run_git(source, "status", "--short").stdout

    workspace = GitWorkspaceAdapter().prepare_workspace(
        contribution_entry(source=str(source), source_type="local_git_repo"),
        str(tmp_path / "contributions"),
    )

    checkout_skill_file = (
        Path(workspace.checkout_path) / "skills" / "code-review" / "SKILL.md"
    )
    assert Path(workspace.checkout_path) != source
    assert checkout_skill_file.is_file()
    assert workspace.has_usable_origin is False
    assert run_git(source, "status", "--short").stdout == status_before
    assert untracked.read_text(encoding="utf-8") == "keep me\n"


def test_git_workspace_sanitizes_git_failure_output(tmp_path: Path) -> None:
    entry = contribution_entry(source="https://token@example.com/private/skills.git")
    checkout_path = expected_checkout_path(tmp_path, entry)
    clone_command = (
        "git",
        "--no-pager",
        "clone",
        "--",
        entry.source,
        str(checkout_path),
    )
    runner = RecordingRunner(
        {clone_command: (1, "", "fatal: token@example.com authentication failed")},
    )

    with pytest.raises(ContributionGitError) as exc_info:
        GitWorkspaceAdapter(runner=runner).prepare_workspace(entry, str(tmp_path))

    assert str(exc_info.value) == "git contribution workspace operation failed"
    assert "token" not in str(exc_info.value)
    assert "example.com" not in str(exc_info.value)


def contribution_entry(
    *,
    requirement: str = "platform-skills/code-review",
    skill_name: str = "code-review",
    skill_path: str = "skills/code-review",
    source: str = "git@example.com:example/skills.git",
    source_type: str = "git_url",
) -> ContributionLockfileEntry:
    return ContributionLockfileEntry(
        requirement=requirement,
        index_name="platform-skills",
        skill_name=skill_name,
        target=".agents/skills/code-review",
        source=source,
        source_type=source_type,
        source_revision="abc123",
        skill_path=skill_path,
        skill_file=f"{skill_path}/SKILL.md",
        index_schema_version=1,
    )


def contribution_workspace() -> ContributionWorkspace:
    return ContributionWorkspace(
        checkout_path="/tmp/ritebook/contributions/source/platform-skills-code-review",
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )


def expected_checkout_path(
    contribution_root: Path,
    entry: ContributionLockfileEntry,
) -> Path:
    source_digest = hashlib.sha256(entry.source.encode()).hexdigest()[:16]
    skill_digest = hashlib.sha256(entry.requirement.encode()).hexdigest()[:8]
    skill_slug = entry.skill_path.replace("/", "-")
    checkout_name = f"{entry.index_name}-{skill_slug}-{skill_digest}"
    return contribution_root / source_digest / checkout_name


def git(checkout_path: Path, *arguments: str) -> tuple[str, ...]:
    return ("git", "--no-pager", "-C", str(checkout_path), *arguments)


def run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    git_executable = which("git")
    if git_executable is None:
        message = "git executable is required"
        raise RuntimeError(message)
    return subprocess.run(  # noqa: S603
        (git_executable, "--no-pager", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )


def write_workspace_marker(checkout_path: Path) -> None:
    marker = checkout_path / ".git" / git_workspace_adapter.WORKSPACE_MARKER_NAME
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("managed by Ritebook\n", encoding="utf-8")
