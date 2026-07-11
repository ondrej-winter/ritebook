"""Outbound port for user installation manifest persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallationManifestEntry,
    )


class InstallationManifestPort(Protocol):
    """Outbound dependency for writing generated installation state."""

    def write_installation(
        self,
        entry: InstallationManifestEntry,
        registry_path: str | None,
        *,
        force: bool,
    ) -> None:
        """Persist a generated direct-install manifest entry."""
