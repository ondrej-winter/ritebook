"""Outbound port for strict generated installation state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        GeneratedStateFile,
        InstallationOperationPaths,
        InstallationStateSnapshot,
        OwnedInstallation,
        ReconciliationIssue,
        SyncPaths,
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
    ) -> SyncPaths:
        """Resolve only the selected sync lockfile path."""

    def read_ownership(self, ownership_path: str) -> InstallationStateSnapshot:
        """Read strict ownership state and the digest of the exact parsed bytes."""

    def read_lockfile_ownership(
        self,
        lockfile_path: str,
        *,
        requirements_file: str,
    ) -> InstallationStateSnapshot:
        """Read lock state as constrained ownership with its exact-byte digest."""

    def ownership_file(
        self,
        entries: tuple[OwnedInstallation, ...],
        ownership_path: str,
        *,
        expected_digest: str | None = None,
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
