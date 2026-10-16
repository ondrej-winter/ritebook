"""Skill installation command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from ritebook.features.skill_installation.application.dtos import (
    InstallFromRequirementsCommand,
    InstallSkillCommand,
)
from ritebook.features.skill_installation.application.errors import (
    InstallationPersistenceError,
    SkillInstallationError,
    UnsafeInstallPathError,
)
from ritebook.shared_kernel import escape_terminal_control_characters

if TYPE_CHECKING:
    import argparse

    from ritebook.features.skill_installation.application.dtos import ReconciliationIssue
    from ritebook.features.skill_installation.application.ports import (
        InstallFromRequirementsPort,
        InstallSkillPort,
    )


def run_install_skill(
    args: argparse.Namespace,
    *,
    install_skill: InstallSkillPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run install-skill against the injected application port."""
    try:
        command = InstallSkillCommand(
            skill_reference=args.skill_reference,
            target=args.target,
            force=args.force,
            registry_path=args.registry_path,
            installation_registry_path=args.installation_registry_path,
        )
        result = install_skill.execute(command)
    except (SkillInstallationError, ValueError) as err:
        print(_error_message(err), file=stderr)
        return 1
    print(f"Installed {result.requirement} to {result.target}", file=stdout)
    return 0


def run_install(
    args: argparse.Namespace,
    *,
    install_from_requirements: InstallFromRequirementsPort,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Run install against the injected requirements-install application port."""
    try:
        command = InstallFromRequirementsCommand(
            requirements_file=args.requirements_file,
            force=args.force,
            registry_path=args.registry_path,
            lockfile_path=args.lockfile,
        )
        result = install_from_requirements.execute(command)
    except (SkillInstallationError, ValueError) as err:
        message = _error_message(err)
        if isinstance(err, (InstallationPersistenceError, UnsafeInstallPathError)):
            message += (
                "; sync may have partially completed. Inspect targets and the lockfile; "
                "rerun normally to identify preserved mismatches, then review every current "
                "declaration before a destructive --force repair."
            )
        print(message, file=stderr)
        return 1
    requirements_file = escape_terminal_control_characters(result.requirements_file)
    print(
        f"Reconciled skills from {requirements_file}: "
        f"installed {result.installed_count}, updated {result.updated_count}, "
        f"unchanged {result.unchanged_count}",
        file=stdout,
    )
    for issue in result.issues:
        code = escape_terminal_control_characters(issue.code)
        target = escape_terminal_control_characters(issue.target)
        detail = escape_terminal_control_characters(_issue_detail(issue, command))
        print(
            f"ritebook: issue: {code}: {target}: {detail}",
            file=stderr,
        )
    return 1 if result.issues else 0


def _issue_detail(issue: ReconciliationIssue, command: InstallFromRequirementsCommand) -> str:
    detail = issue.detail
    if issue.code not in {"local-changes", "unmanaged-target"}:
        return detail
    detail += (
        "; --force destructively replaces all selected targets. "
        "Review every current declaration before rerunning sync with --force."
    )
    if issue.code == "local-changes" and issue.requirement is not None:
        root = Path(command.requirements_file).expanduser().resolve(strict=False).parent
        lockfile = (
            Path(command.lockfile_path).expanduser().resolve(strict=False)
            if command.lockfile_path is not None
            else root / "ritebook.lock"
        )
        contribution = shlex.join(["ritebook", "skills", "contribute", issue.requirement, "--lockfile", str(lockfile)])
        detail += (
            f" Prepare a local contribution with cd {shlex.quote(str(root))} && {contribution} "
            "(manual push/review follows)."
        )
    return detail


def _error_message(err: Exception) -> str:
    detail = escape_terminal_control_characters(str(err))
    return f"ritebook: error: {detail}"
