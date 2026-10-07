"""Outbound port for exclusive recoverable installation transactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from ritebook.features.skill_installation.application.dtos import GeneratedStateFile


class InstallationTransaction(Protocol):
    """One locked target-and-state transaction."""

    def replace_tree(
        self,
        *,
        staged_path: str,
        target_path: str,
        expected_digest: str | None,
    ) -> None:
        """Place a staged tree while retaining prior target state."""

    def remove_tree(self, *, target_path: str, expected_digest: str) -> None:
        """Remove an unchanged owned tree while retaining it for rollback."""

    def commit_state(self, files: tuple[GeneratedStateFile, ...]) -> None:
        """Commit all generated-state candidates."""


class InstallationTransactionPort(Protocol):
    """Acquire one exclusive installation operation transaction."""

    def open(
        self,
        *,
        lock_path: str,
        journal_path: str,
    ) -> AbstractContextManager[InstallationTransaction]:
        """Recover prior work and open a locked transaction."""
