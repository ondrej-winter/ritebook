"""Inbound port for requirements-file skill installation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallFromRequirementsCommand,
        InstallFromRequirementsResult,
    )


class InstallFromRequirementsPort(Protocol):
    """Inbound dependency for installing declared skill requirements."""

    def execute(
        self,
        command: InstallFromRequirementsCommand,
    ) -> InstallFromRequirementsResult:
        """Install declared skills and return generated lockfile metadata."""
