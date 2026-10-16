"""Outbound writes for sync with no operation lock or durable recovery state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import GeneratedStateFile


class SyncWriterPort(Protocol):
    """Place individual staged trees and atomically replace a complete lockfile."""

    def replace_tree(
        self,
        *,
        staged_path: str,
        target_path: str,
        expected_digest: str | None,
    ) -> None:
        """Revalidate and replace one target, without retaining batch backups."""

    def write_lockfile(self, candidate: GeneratedStateFile) -> None:
        """Atomically persist lock bytes without snapshot comparison or rollback."""
