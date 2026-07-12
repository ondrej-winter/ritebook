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
    command = InstallSkillCommand(
        skill_reference=args.skill_reference,
        target=args.target,
        force=args.force,
        registry_path=args.registry_path,
        installation_registry_path=args.installation_registry_path,
    )
    try:
        result = install_skill.execute(command)
    except (SkillInstallationError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
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
    command = InstallFromRequirementsCommand(
        requirements_file=args.requirements_file,
        force=args.force,
        registry_path=args.registry_path,
        lockfile_path=args.lockfile,
    )
    try:
        result = install_from_requirements.execute(command)
    except (SkillInstallationError, ValueError) as err:
        print(f"ritebook: error: {err}", file=stderr)
        return 1
    print(
        f"Installed {result.installed_count} skill(s) from {result.requirements_file}",
        file=stdout,
    )
    return 0
