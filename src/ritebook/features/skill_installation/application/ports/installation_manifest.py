"""Outbound port for user installation manifest persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallationManifestEntry,
        LockfileManifestEntry,
    )


class InstallationManifestPort(Protocol):
    """Outbound dependency for writing generated installation state."""

    def validate_installation(
        self,
        entry: InstallationManifestEntry,
        registry_path: str | None,
        *,
        force: bool,
    ) -> None:
        """Validate a direct-install state update without filesystem mutation."""

    def write_installation(
        self,
        entry: InstallationManifestEntry,
        registry_path: str | None,
        *,
        force: bool,
    ) -> None:
        """Persist a generated direct-install manifest entry."""

    def validate_lockfile(
        self,
        entries: tuple[LockfileManifestEntry, ...],
        lockfile_path: str | None,
        *,
        requirements_file: str,
    ) -> None:
        """Validate a lockfile update without filesystem mutation."""

    def write_lockfile(
        self,
        entries: tuple[LockfileManifestEntry, ...],
        lockfile_path: str | None,
        *,
        requirements_file: str,
    ) -> None:
        """Persist generated repo-local lockfile entries."""
