"""CLI command handlers for the skill installation feature."""

from ritebook.features.skill_installation.adapters.inbound.cli.commands import (
    run_install,
    run_install_skill,
)

__all__ = ["run_install", "run_install_skill"]
