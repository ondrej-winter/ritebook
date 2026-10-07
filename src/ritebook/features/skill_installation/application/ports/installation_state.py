"""Outbound port for strict generated installation state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        GeneratedStateFile,
        InstallationOperationPaths,
        OwnedInstallation,
        ReconciliationIssue,
    )


class InstallationStatePort(Protocol):
    """Resolve, read, and render generated installation state."""

    def direct_paths(self, registry_path: str | None) -> InstallationOperationPaths:
        """Resolve direct-install operation paths."""

    def sync_paths(
        self,
        *,
        requirements_file: str,
        lockfile_path: str | None,
    ) -> InstallationOperationPaths:
        """Resolve repository-sync operation paths."""

    def read_ownership(self, ownership_path: str) -> tuple[OwnedInstallation, ...]:
        """Read strict ownership state, or return an empty state when absent."""

    def ownership_exists(self, ownership_path: str) -> bool:
        """Return whether a local ownership ledger exists."""

    def read_lockfile_ownership(
        self,
        lockfile_path: str,
        *,
        requirements_file: str,
    ) -> tuple[OwnedInstallation, ...]:
        """Read portable schema-v2 lock state as constrained sync ownership."""

    def ownership_file(
        self,
        entries: tuple[OwnedInstallation, ...],
        ownership_path: str,
    ) -> GeneratedStateFile:
        """Render a complete private ownership-state candidate."""

    def lockfile(
        self,
        entries: tuple[OwnedInstallation, ...],
        issues: tuple[ReconciliationIssue, ...],
        lockfile_path: str,
        *,
        requirements_file: str,
    ) -> GeneratedStateFile:
        """Render a portable complete or mixed lockfile candidate."""
