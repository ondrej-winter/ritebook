import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from ritebook.features.skill_contribution.adapters.outbound import (
    contribution_checkout,
)
from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionGitError,
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
        returncode, stdout, stderr = self.responses.get(tuple(recorded), (0, "", ""))
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def test_contribution_checkout_creates_safe_timestamped_branch() -> None:
    workspace = contribution_workspace()
    runner = RecordingRunner()
    adapter = contribution_checkout.ContributionCheckoutAdapter(
        runner=runner,
        clock=lambda: datetime(2026, 7, 18, 20, 15, 34, tzinfo=UTC),
    )

    branch_name = adapter.prepare_branch(contribution_entry(), workspace)

    assert branch_name == "ritebook/skills-code-review-20260718201534"
    assert runner.commands == [
        [
            "git",
            "--no-pager",
            "-C",
            workspace.checkout_path,
            "checkout",
            "-B",
            branch_name,
            workspace.current_base_revision,
        ],
    ]


def test_contribution_checkout_stages_only_skill_and_index_then_commits() -> None:
    entry = contribution_entry()
    workspace = contribution_workspace()
    branch_name = "ritebook/skills-code-review-20260718201534"
    runner = RecordingRunner(
        {
            git(workspace, "config", "--get", "user.name"): (0, "Ritebook User\n", ""),
            git(workspace, "config", "--get", "user.email"): (
                0,
                "ritebook@example.invalid\n",
                "",
            ),
            git(workspace, "rev-parse", "HEAD"): (0, "def456789\n", ""),
        },
    )

    prepared = contribution_checkout.ContributionCheckoutAdapter(
        runner=runner,
    ).commit_changes(
        entry,
        workspace,
        branch_name,
    )

    assert runner.commands == [
        [*git(workspace, "config", "--get", "user.name")],
        [*git(workspace, "config", "--get", "user.email")],
        [*git(workspace, "add", "--", entry.skill_path, "ritebook-index.json")],
        [
            *git(
                workspace,
                "commit",
                "--no-gpg-sign",
                "--message",
                "Update code-review skill from Ritebook contribution",
                "--",
            ),
        ],
        [*git(workspace, "rev-parse", "HEAD")],
    ]
    assert prepared.skill_reference == entry.requirement
    assert prepared.checkout_path == workspace.checkout_path
    assert prepared.branch_name == branch_name
    assert prepared.commit_hash == "def456789"
    assert prepared.push_command == f"git push origin {branch_name}"


def test_contribution_checkout_omits_push_command_without_usable_origin() -> None:
    entry = contribution_entry()
    workspace = contribution_workspace(has_usable_origin=False)
    runner = successful_commit_runner(workspace)

    prepared = contribution_checkout.ContributionCheckoutAdapter(
        runner=runner,
    ).commit_changes(
        entry,
        workspace,
        "ritebook/skills-code-review-20260718201534",
    )

    assert prepared.push_command is None


def test_contribution_checkout_reports_missing_commit_identity() -> None:
    entry = contribution_entry()
    workspace = contribution_workspace()
    runner = RecordingRunner(
        {git(workspace, "config", "--get", "user.name"): (1, "", "missing")},
    )

    with pytest.raises(
        ContributionGitError,
        match="Git commit identity is not configured",
    ):
        contribution_checkout.ContributionCheckoutAdapter(runner=runner).commit_changes(
            entry,
            workspace,
            "ritebook/skills-code-review-20260718201534",
        )

    assert runner.commands == [[*git(workspace, "config", "--get", "user.name")]]


def test_contribution_checkout_sanitizes_commit_failure() -> None:
    entry = contribution_entry()
    workspace = contribution_workspace()
    commit_command = git(
        workspace,
        "commit",
        "--no-gpg-sign",
        "--message",
        "Update code-review skill from Ritebook contribution",
        "--",
    )
    runner = RecordingRunner(
        {
            git(workspace, "config", "--get", "user.name"): (0, "User\n", ""),
            git(workspace, "config", "--get", "user.email"): (
                0,
                "user@example.invalid\n",
                "",
            ),
            commit_command: (1, "", "fatal: https://secret@example.com failed"),
        },
    )

    with pytest.raises(ContributionGitError) as exc_info:
        contribution_checkout.ContributionCheckoutAdapter(runner=runner).commit_changes(
            entry,
            workspace,
            "ritebook/skills-code-review-20260718201534",
        )

    assert str(exc_info.value) == (
        "git contribution commit failed; the checkout remains available for inspection"
    )
    assert "secret" not in str(exc_info.value)


def contribution_entry() -> ContributionLockfileEntry:
    return ContributionLockfileEntry(
        requirement="platform-skills/code-review",
        index_name="platform-skills",
        skill_name="code-review",
        target=".agents/skills/code-review",
        source="git@example.com:example/skills.git",
        source_type="git_url",
        source_revision="abc123",
        skill_path="skills/code-review",
        skill_file="skills/code-review/SKILL.md",
        index_schema_version=1,
    )


def contribution_workspace(
    *,
    has_usable_origin: bool = True,
) -> ContributionWorkspace:
    return ContributionWorkspace(
        checkout_path="/tmp/ritebook/contributions/source/platform-skills-code-review",
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=has_usable_origin,
    )


def successful_commit_runner(workspace: ContributionWorkspace) -> RecordingRunner:
    return RecordingRunner(
        {
            git(workspace, "config", "--get", "user.name"): (0, "User\n", ""),
            git(workspace, "config", "--get", "user.email"): (
                0,
                "user@example.invalid\n",
                "",
            ),
            git(workspace, "rev-parse", "HEAD"): (0, "def456789\n", ""),
        },
    )


def git(workspace: ContributionWorkspace, *arguments: str) -> tuple[str, ...]:
    return (
        "git",
        "--no-pager",
        "-C",
        workspace.checkout_path,
        *arguments,
    )
