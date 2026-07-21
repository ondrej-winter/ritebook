"""Prepare isolated Git workspaces for skill contributions."""

from __future__ import annotations

import hashlib
import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

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
from ritebook.features.skill_contribution.application.ports import (
    SkillChangeDetectorPort,
    SkillSourceWorkspacePort,
)

DEFAULT_CONTRIBUTION_ROOT = "~/.cache/ritebook/contributions"
GIT_URL_SOURCE_TYPE = "git_url"
LOCAL_GIT_REPO_SOURCE_TYPE = "local_git_repo"
WORKSPACE_MARKER_NAME = "ritebook-contribution-workspace"
GitRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
BinaryGitRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[bytes]]
ContributionRootResolver = Callable[[], Path]


class GitSkillChangeDetectorAdapter(SkillChangeDetectorPort):
    """Detect upstream changes before comparing installed skill content."""

    def __init__(
        self,
        local_change_detector: SkillChangeDetectorPort,
        runner: GitRunner | None = None,
    ) -> None:
        """Initialize Git inspection and installed-content comparison boundaries."""
        self._local_change_detector = local_change_detector
        self._runner = runner or _run_git

    def compare(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> SkillChangeComparison:
        """Detect selected-path upstream changes, then compare installed content."""
        if not entry.source_revision:
            raise IncompleteContributionProvenanceError(
                entry.requirement,
                "source_revision",
            )
        result = self._runner(
            _git(
                Path(workspace.checkout_path).expanduser(),
                "diff",
                "--quiet",
                entry.source_revision,
                workspace.current_base_revision,
                "--",
                entry.skill_path,
            ),
        )
        if result.returncode == 1:
            return SkillChangeComparison(
                status=SkillChangeStatus.UPSTREAM_CHANGED,
                installed_path=entry.target,
                source_skill_path=entry.skill_path,
                changed_file_count=1,
            )
        if result.returncode != 0:
            msg = "git upstream skill-path inspection failed"
            raise ContributionGitError(msg)
        return self._local_change_detector.compare(entry, workspace)


class GitWorkspaceAdapter(SkillSourceWorkspacePort):
    """Clone or refresh a Ritebook-owned contribution workspace."""

    def __init__(
        self,
        runner: GitRunner | None = None,
        binary_runner: BinaryGitRunner | None = None,
        default_contribution_root: ContributionRootResolver | None = None,
    ) -> None:
        """Initialize injectable Git and default-root boundaries."""
        self._runner = runner or _run_git
        self._binary_runner = binary_runner or _run_git_bytes
        self._default_contribution_root = (
            default_contribution_root or _default_contribution_root
        )

    def prepare_workspace(
        self,
        entry: ContributionLockfileEntry,
        contribution_root: str | None,
    ) -> ContributionWorkspace:
        """Prepare a clean checkout at the current upstream base."""
        _validate_source_type(entry.source_type)
        checkout_path = _checkout_path(
            entry,
            contribution_root,
            self._default_contribution_root,
        )
        if checkout_path.exists():
            _validate_owned_checkout(checkout_path)
        else:
            checkout_path.parent.mkdir(parents=True, exist_ok=True)
            self._run(
                [
                    "git",
                    "--no-pager",
                    "clone",
                    "--",
                    entry.source,
                    str(checkout_path),
                ],
            )
            _write_workspace_marker(checkout_path)
            _validate_owned_checkout(checkout_path)

        has_origin = self._has_origin(checkout_path)
        if has_origin:
            self._run(_git(checkout_path, "fetch", "--prune", "origin"))
        self._verify_locked_provenance(checkout_path, entry)
        base_reference = self._base_reference(checkout_path, has_origin=has_origin)
        self._run(_git(checkout_path, "checkout", "--detach", base_reference))
        self._run(_git(checkout_path, "reset", "--hard", base_reference))
        self._run(_git(checkout_path, "clean", "-fd"))
        current_base_revision = self._read_required_output(
            _git(checkout_path, "rev-parse", "HEAD"),
        )
        return ContributionWorkspace(
            checkout_path=str(checkout_path),
            source_skill_path=entry.skill_path,
            current_base_revision=current_base_revision,
            locked_revision=entry.source_revision,
            has_usable_origin=(has_origin and entry.source_type == GIT_URL_SOURCE_TYPE),
        )

    def _verify_locked_provenance(
        self,
        checkout_path: Path,
        entry: ContributionLockfileEntry,
    ) -> None:
        revision = self._runner(
            _git(
                checkout_path,
                "cat-file",
                "-e",
                f"{entry.source_revision}^{{commit}}",
            ),
        )
        if revision.returncode != 0:
            msg = (
                "locked source revision is unavailable; restore the source history "
                "or reinstall the skill to regenerate ritebook.lock"
            )
            raise ContributionGitError(msg)
        committed_index = self._binary_runner(
            _git(checkout_path, "show", f"{entry.source_revision}:ritebook-index.json"),
        )
        if committed_index.returncode != 0:
            msg = (
                "locked source index is unavailable; restore the source history "
                "or reinstall the skill to regenerate ritebook.lock"
            )
            raise ContributionGitError(msg)
        digest = f"sha256:{hashlib.sha256(committed_index.stdout).hexdigest()}"
        if digest != entry.index_digest:
            msg = (
                "locked source index does not match ritebook.lock; reinstall the skill "
                "to regenerate verified provenance"
            )
            raise ContributionGitError(msg)

    def _has_origin(self, checkout_path: Path) -> bool:
        result = self._runner(_git(checkout_path, "remote", "get-url", "origin"))
        return result.returncode == 0 and bool(result.stdout.strip())

    def _base_reference(self, checkout_path: Path, *, has_origin: bool) -> str:
        if not has_origin:
            return "HEAD"
        command = _git(
            checkout_path,
            "symbolic-ref",
            "--quiet",
            "--short",
            "refs/remotes/origin/HEAD",
        )
        result = self._runner(command)
        reference = result.stdout.strip()
        if result.returncode != 0 or not reference:
            msg = "git contribution workspace could not determine the upstream base"
            raise ContributionGitError(msg)
        return reference

    def _read_required_output(self, command: Sequence[str]) -> str:
        result = self._runner(command)
        value = result.stdout.strip()
        if result.returncode != 0 or not value:
            msg = "git contribution workspace operation failed"
            raise ContributionGitError(msg)
        return value

    def _run(self, command: Sequence[str]) -> None:
        result = self._runner(command)
        if result.returncode != 0:
            msg = "git contribution workspace operation failed"
            raise ContributionGitError(msg)


def _checkout_path(
    entry: ContributionLockfileEntry,
    contribution_root: str | None,
    default_root: ContributionRootResolver,
) -> Path:
    root = (
        Path(contribution_root).expanduser()
        if contribution_root is not None
        else default_root().expanduser()
    )
    source_digest = hashlib.sha256(entry.source.encode("utf-8")).hexdigest()[:16]
    skill_digest = hashlib.sha256(entry.requirement.encode("utf-8")).hexdigest()[:8]
    skill_slug = entry.skill_path.replace("/", "-")
    checkout_path = (
        root / source_digest / f"{entry.index_name}-{skill_slug}-{skill_digest}"
    )
    current = root
    for part in checkout_path.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            msg = "git contribution workspace path contains a symlink"
            raise ContributionGitError(msg)
    try:
        resolved_root = root.resolve(strict=False)
        resolved_checkout = checkout_path.resolve(strict=False)
    except OSError as err:
        msg = "git contribution workspace path could not be resolved safely"
        raise ContributionGitError(msg) from err
    if not resolved_checkout.is_relative_to(resolved_root):
        msg = "git contribution workspace path escapes the contribution root"
        raise ContributionGitError(msg)
    return checkout_path


def _validate_owned_checkout(checkout_path: Path) -> None:
    git_directory = checkout_path / ".git"
    workspace_marker = git_directory / WORKSPACE_MARKER_NAME
    if (
        not checkout_path.is_dir()
        or checkout_path.is_symlink()
        or not git_directory.is_dir()
        or git_directory.is_symlink()
        or not workspace_marker.is_file()
        or workspace_marker.is_symlink()
    ):
        msg = "git contribution workspace is not a reusable Ritebook-owned clone"
        raise ContributionGitError(msg)


def _write_workspace_marker(checkout_path: Path) -> None:
    marker = checkout_path / ".git" / WORKSPACE_MARKER_NAME
    try:
        marker.write_text("managed by Ritebook\n", encoding="utf-8")
    except OSError as err:
        msg = "git contribution workspace ownership marker could not be written"
        raise ContributionGitError(msg) from err


def _validate_source_type(source_type: str) -> None:
    if source_type not in {GIT_URL_SOURCE_TYPE, LOCAL_GIT_REPO_SOURCE_TYPE}:
        msg = "unsupported source type for skill contribution"
        raise ContributionGitError(msg)


def _git(checkout_path: Path, *arguments: str) -> tuple[str, ...]:
    return ("git", "--no-pager", "-C", str(checkout_path), *arguments)


def _default_contribution_root() -> Path:
    return Path(DEFAULT_CONTRIBUTION_ROOT)


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


def _run_git_bytes(command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_PAGER"] = "cat"
    environment.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    return subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
        env=environment,
    )
