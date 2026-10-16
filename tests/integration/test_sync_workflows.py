from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

import pytest

from tests.integration.sync_support import REFERENCE, create_sync_project

if TYPE_CHECKING:
    from pathlib import Path

    from tests.integration.conftest import GitRepositoryFactory


@pytest.mark.parametrize("ledger", ["conflicting", "malformed"])
def test_sync_custom_lockfile_survives_relocation_and_ignores_legacy_artifacts(
    tmp_path: Path,
    git_repository: GitRepositoryFactory,
    ledger: str,
) -> None:
    project = create_sync_project(tmp_path, git_repository)
    assert project.sync().returncode == 0
    before = project.lockfile.read_bytes()
    legacy = project.consumer / ".ritebook"
    legacy.mkdir()
    for name, content in {
        "installations.json": b"malformed ledger",
        "transaction.json": b"malformed journal",
        "install.lock": b"old lock",
        "user.txt": b"unrelated sentinel",
    }.items():
        (legacy / name).write_bytes(content)
    if ledger == "conflicting":
        entry = json.loads(before)["skills"][0]
        entry.update(workflow="sync", canonical_target=str(project.target), installed_tree_digest=f"sha256:{'0' * 64}")
        (legacy / "installations.json").write_text(json.dumps({"schema_version": 3, "installations": [entry]}))
    old = {path.name: path.read_bytes() for path in legacy.iterdir()}
    relocated = tmp_path / "relocated"
    shutil.move(str(project.consumer), relocated)
    project.consumer = relocated
    result = project.sync()
    assert result.returncode == 0, result.stderr
    assert "unchanged 1" in result.stdout
    assert project.lockfile.read_bytes() == before
    assert {path.name: path.read_bytes() for path in (relocated / ".ritebook").iterdir()} == old


def test_preserved_edit_remains_contributable_using_only_custom_lockfile(
    tmp_path: Path,
    git_repository: GitRepositoryFactory,
) -> None:
    project = create_sync_project(tmp_path, git_repository)
    assert project.sync().returncode == 0
    baseline = json.loads(project.lockfile.read_bytes())["skills"][0]
    edited = project.target / "guide.md"
    edited.write_text("local contribution\n")
    skipped = project.sync()
    assert skipped.returncode == 1
    assert f"skills contribute {REFERENCE} --lockfile {project.lockfile}" in skipped.stderr
    preserved = json.loads(project.lockfile.read_bytes())["skills"][0]
    assert preserved["installed_tree_digest"] == baseline["installed_tree_digest"]
    assert preserved["source_revision"] == baseline["source_revision"]
    assert preserved["status"] == "local_changes"
    contribution_root = tmp_path / "contributions"
    result = project.cli(
        "skills",
        "contribute",
        REFERENCE,
        "--lockfile",
        str(project.lockfile),
        "--contribution-root",
        str(contribution_root),
    )
    assert result.returncode == 0, result.stderr
    assert f"Prepared contribution for {REFERENCE}" in result.stdout
    assert "git push origin" in result.stdout
    [changed] = contribution_root.glob("*/*/skills/code-review/guide.md")
    assert changed.read_text() == "local contribution\n"
    assert (project.upstream.path / "skills/code-review/guide.md").read_text() == "original verified guide\n"
    assert not (project.consumer / ".ritebook").exists()


@pytest.mark.parametrize("content", ['{"schema_version":1}', "malformed"])
@pytest.mark.parametrize("force", [False, True])
def test_invalid_selected_lockfile_remains_fatal_despite_old_ledger(
    tmp_path: Path,
    git_repository: GitRepositoryFactory,
    content: str,
    *,
    force: bool,
) -> None:
    project = create_sync_project(tmp_path, git_repository)
    legacy = project.consumer / ".ritebook"
    legacy.mkdir()
    (legacy / "installations.json").write_bytes(b"malformed old ledger")
    project.lockfile.parent.mkdir()
    project.lockfile.write_text(content)
    result = project.sync(force=force)
    assert result.returncode == 1
    assert not project.target.exists()
    assert project.lockfile.read_text() == content
    assert (legacy / "installations.json").read_bytes() == b"malformed old ledger"
