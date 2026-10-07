"""Skill installation command handlers for the Ritebook CLI adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ritebook.features.skill_installation.application.dtos import (
    InstallFromRequirementsCommand,
    InstallSkillCommand,
)
from ritebook.features.skill_installation.application.errors import (
    SkillInstallationError,
)
from ritebook.shared_kernel import escape_terminal_control_characters

if TYPE_CHECKING:
    import argparse

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
        print(_error_message(err), file=stderr)
        return 1
    print(
        f"Reconciled skills from {result.requirements_file}: "
        f"installed {result.installed_count}, updated {result.updated_count}, "
        f"unchanged {result.unchanged_count}, pruned {result.pruned_count}",
        file=stdout,
    )
    for issue in result.issues:
        code = escape_terminal_control_characters(issue.code)
        target = escape_terminal_control_characters(issue.target)
        detail = escape_terminal_control_characters(issue.detail)
        print(
            f"ritebook: issue: {code}: {target}: {detail}",
            file=stderr,
        )
    return 1 if result.issues else 0


def _error_message(err: Exception) -> str:
    detail = escape_terminal_control_characters(str(err))
    return f"ritebook: error: {detail}"
