from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest

from tests.integration.sync_support import HELPER, create_sync_project

if TYPE_CHECKING:
    from pathlib import Path

    from tests.integration.conftest import GitRepositoryFactory


@pytest.mark.parametrize("baseline", ["stale", "absent"])
def test_interrupted_sync_preserves_uncertainty_until_reviewed_force_repair(
    tmp_path: Path,
    git_repository: GitRepositoryFactory,
    baseline: str,
) -> None:
    project = create_sync_project(tmp_path, git_repository)
    previous_lock: bytes | None = None
    previous_digest: str | None = None
    if baseline == "stale":
        installed = project.sync()
        assert installed.returncode == 0, installed.stderr
        previous_lock = project.lockfile.read_bytes()
        previous_digest = json.loads(previous_lock)["skills"][0]["installed_tree_digest"]
        project.advance_source("different verified guide\n")
    ready = tmp_path / "before-lockfile.ready"
    process = subprocess.Popen(  # noqa: S603 - bounded isolated process-kill test.
        [sys.executable, str(HELPER), "pause-before-lockfile", str(ready), *project.sync_arguments()],
        cwd=project.consumer,
        env=project.environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists():
            assert process.poll() is None, process.communicate(timeout=2)
            if time.monotonic() >= deadline:
                pytest.fail("timed out waiting for replacement-before-lockfile marker")
            time.sleep(0.01)
        expected = "different verified guide\n" if baseline == "stale" else "original verified guide\n"
        assert (project.target / "guide.md").read_text() == expected
        if previous_lock is None:
            assert not project.lockfile.exists()
        else:
            assert project.lockfile.read_bytes() == previous_lock
        process.send_signal(signal.SIGKILL)
        assert process.wait(timeout=5) == -signal.SIGKILL
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    preserved = project.sync()
    assert preserved.returncode == 1
    assert "local-changes" in preserved.stderr if baseline == "stale" else "unmanaged-target" in preserved.stderr
    assert (project.target / "guide.md").read_text() == expected
    partial = json.loads(project.lockfile.read_bytes())
    assert partial["state"] == "partial"
    if previous_digest is not None:
        assert partial["skills"][0]["installed_tree_digest"] == previous_digest
    else:
        assert partial["skills"] == []
        assert "contribute" not in preserved.stderr
    repaired = project.sync(force=True)
    assert repaired.returncode == 0, repaired.stderr
    complete = json.loads(project.lockfile.read_bytes())
    assert complete["state"] == "complete"
    assert complete["skills"][0]["status"] == "materialized"
    if previous_digest is not None:
        assert complete["skills"][0]["installed_tree_digest"] != previous_digest
    assert not (project.consumer / ".ritebook").exists()
