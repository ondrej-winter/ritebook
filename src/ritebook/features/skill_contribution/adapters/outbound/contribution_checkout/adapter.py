"""Create branches and commits in isolated contribution checkouts."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
    PreparedContribution,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionGitError,
)
from ritebook.features.skill_contribution.application.ports import (
    ContributionCheckoutPort,
)

GitRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
Clock = Callable[[], datetime]


class ContributionCheckoutAdapter(ContributionCheckoutPort):
    """Create contribution branches and scoped commits."""

    def __init__(
        self,
        runner: GitRunner | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize injectable Git and clock boundaries."""
        self._runner = runner or _run_git
        self._clock = clock or _utc_now

    def prepare_branch(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> str:
        """Create a timestamped branch from the prepared upstream base."""
        timestamp = self._clock().astimezone(UTC).strftime("%Y%m%d%H%M%S")
        skill_slug = entry.skill_path.replace("/", "-")
        branch_name = f"ritebook/{skill_slug}-{timestamp}"
        self._run(
            _git(
                workspace,
                "checkout",
                "-B",
                branch_name,
                workspace.current_base_revision,
            ),
            failure_message="git contribution branch operation failed",
        )
        return branch_name

    def commit_changes(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
        branch_name: str,
    ) -> PreparedContribution:
        """Stage the selected skill and index, commit, and return safe metadata."""
        self._require_commit_identity(workspace)
        self._run(
            _git(
                workspace,
                "add",
                "--",
                entry.skill_path,
                "ritebook-index.json",
            ),
            failure_message="git contribution staging failed",
        )
        self._run(
            _git(
                workspace,
                "commit",
                "--no-gpg-sign",
                "--message",
                f"Update {entry.skill_name} skill from Ritebook contribution",
                "--",
            ),
            failure_message=(
                "git contribution commit failed; the checkout remains available "
                "for inspection"
            ),
        )
        commit_hash = self._read_required_output(
            _git(workspace, "rev-parse", "HEAD"),
            failure_message="git contribution commit metadata could not be read",
        )
        push_command = (
            f"git push origin {branch_name}" if workspace.has_usable_origin else None
        )
        return PreparedContribution(
            skill_reference=entry.requirement,
            checkout_path=workspace.checkout_path,
            branch_name=branch_name,
            commit_hash=commit_hash,
            push_command=push_command,
        )

    def _require_commit_identity(self, workspace: ContributionWorkspace) -> None:
        for key in ("user.name", "user.email"):
            result = self._runner(_git(workspace, "config", "--get", key))
            if result.returncode != 0 or not result.stdout.strip():
                msg = (
                    "Git commit identity is not configured; set user.name and "
                    "user.email before retrying"
                )
                raise ContributionGitError(msg)

    def _read_required_output(
        self,
        command: Sequence[str],
        *,
        failure_message: str,
    ) -> str:
        result = self._runner(command)
        value = result.stdout.strip()
        if result.returncode != 0 or not value:
            raise ContributionGitError(failure_message)
        return value

    def _run(self, command: Sequence[str], *, failure_message: str) -> None:
        result = self._runner(command)
        if result.returncode != 0:
            raise ContributionGitError(failure_message)


def _git(workspace: ContributionWorkspace, *arguments: str) -> tuple[str, ...]:
    checkout_path = str(Path(workspace.checkout_path).expanduser())
    return ("git", "--no-pager", "-C", checkout_path, *arguments)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _run_git(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_PAGER"] = "cat"
    environment.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    return subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
