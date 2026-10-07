from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from ritebook.features.skill_installation.adapters.outbound import (
    FilesystemInstallationTransactionAdapter,
)

HELPER = Path(__file__).with_name("installation_process_helper.py")


def test_installation_lock_excludes_real_concurrent_process(tmp_path: Path) -> None:
    lock_path = tmp_path / ".ritebook" / "install.lock"
    journal_path = tmp_path / ".ritebook" / "transaction.json"
    ready_path = tmp_path / "holder.ready"
    release_path = tmp_path / "holder.release"
    holder = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            str(HELPER),
            "hold-lock",
            str(lock_path),
            str(journal_path),
            str(ready_path),
            str(release_path),
        ],
        env=_subprocess_environment(),
    )
    try:
        _wait_for_path(ready_path)
        contender = subprocess.run(  # noqa: S603
            [
                sys.executable,
                str(HELPER),
                "try-lock",
                str(lock_path),
                str(journal_path),
            ],
            check=False,
            env=_subprocess_environment(),
            timeout=5,
        )

        assert contender.returncode == 23
    finally:
        release_path.touch()
        assert holder.wait(timeout=5) == 0


def test_next_operation_recovers_after_real_process_kill(tmp_path: Path) -> None:
    lock_path = tmp_path / ".ritebook" / "install.lock"
    journal_path = tmp_path / ".ritebook" / "transaction.json"
    target = tmp_path / "skills" / "code-review"
    staged = tmp_path / "candidate"
    ready_path = tmp_path / "mutation.ready"
    target.mkdir(parents=True)
    staged.mkdir()
    (target / "SKILL.md").write_text("old\n", encoding="utf-8")
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")
    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            str(HELPER),
            "replace-and-wait",
            str(lock_path),
            str(journal_path),
            str(target),
            str(staged),
            str(ready_path),
        ],
        env=_subprocess_environment(),
    )
    try:
        _wait_for_path(ready_path)
        assert (target / "SKILL.md").read_text(encoding="utf-8") == "new\n"
        assert journal_path.is_file()
        process.send_signal(signal.SIGKILL)
        assert process.wait(timeout=5) == -signal.SIGKILL
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    with FilesystemInstallationTransactionAdapter().open(
        lock_path=str(lock_path),
        journal_path=str(journal_path),
    ):
        pass

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "old\n"
    assert not journal_path.exists()
    assert not list(target.parent.glob(".code-review.ritebook-*.previous"))


def _wait_for_path(path: Path) -> None:
    deadline = time.monotonic() + 5
    while not path.exists():
        if time.monotonic() >= deadline:
            message = f"timed out waiting for subprocess marker: {path}"
            raise TimeoutError(message)
        time.sleep(0.01)


def _subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    source_root = Path(__file__).parents[2] / "src"
    environment["PYTHONPATH"] = str(source_root)
    return environment
