"""Subprocess helper for real installation lock and interruption tests."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from ritebook.features.skill_installation.adapters.outbound import (
    FilesystemInstallationTransactionAdapter,
)
from ritebook.features.skill_installation.application.errors import (
    InstallationBusyError,
)


def main(arguments: list[str]) -> int:
    """Run one non-interactive process-level installation scenario."""
    mode, lock_path, journal_path, *rest = arguments
    if mode == "hold-lock":
        ready_path, release_path = map(Path, rest)
        with FilesystemInstallationTransactionAdapter().open(
            lock_path=lock_path,
            journal_path=journal_path,
        ):
            ready_path.write_text("ready\n", encoding="utf-8")
            while not release_path.exists():
                time.sleep(0.01)
        return 0
    if mode == "try-lock":
        try:
            with FilesystemInstallationTransactionAdapter(
                lock_timeout_seconds=0.05,
            ).open(
                lock_path=lock_path,
                journal_path=journal_path,
            ):
                return 0
        except InstallationBusyError:
            return 23
    if mode == "replace-and-wait":
        target_path, staged_path, ready_path = map(Path, rest)
        with FilesystemInstallationTransactionAdapter().open(
            lock_path=lock_path,
            journal_path=journal_path,
        ) as transaction:
            transaction.replace_tree(
                staged_path=str(staged_path),
                target_path=str(target_path),
                expected_digest=transaction.tree_digest(str(target_path)),
            )
            ready_path.write_text("ready\n", encoding="utf-8")
            time.sleep(60)
        return 0
    message = f"unsupported helper mode: {mode}"
    raise ValueError(message)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
