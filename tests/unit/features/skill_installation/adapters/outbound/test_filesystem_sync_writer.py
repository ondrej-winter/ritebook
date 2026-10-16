from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound.filesystem_sync_writer import (
    FilesystemSyncWriterAdapter,
)
from ritebook.features.skill_installation.adapters.outbound.filesystem_sync_writer import (
    adapter as writer_module,
)
from ritebook.features.skill_installation.adapters.outbound.tree_digest import canonical_tree_digest
from ritebook.features.skill_installation.application.dtos import GeneratedStateFile
from ritebook.features.skill_installation.application.errors import InstallationPersistenceError, UnsafeInstallPathError


def test_sync_writer_replaces_one_tree_without_bookkeeping(tmp_path: Path) -> None:
    target = _tree(tmp_path / "target", "old")
    staged = _tree(tmp_path / "staged", "new")
    writer = FilesystemSyncWriterAdapter()
    writer.replace_tree(staged_path=str(staged), target_path=str(target), expected_digest=canonical_tree_digest(target))
    assert (target / "SKILL.md").read_text() == "new"
    assert set(tmp_path.iterdir()) == {target}


def test_sync_writer_rejects_changed_target(tmp_path: Path) -> None:
    target = _tree(tmp_path / "target", "old")
    digest = canonical_tree_digest(target)
    (target / "SKILL.md").write_text("edited")
    staged = _tree(tmp_path / "staged", "new")
    with pytest.raises(InstallationPersistenceError, match="changed after inspection"):
        FilesystemSyncWriterAdapter().replace_tree(
            staged_path=str(staged), target_path=str(target), expected_digest=digest
        )
    assert (target / "SKILL.md").read_text() == "edited"
    assert staged.is_dir()


@pytest.mark.parametrize("exists", [False, True])
def test_sync_writer_lockfile_is_atomic_on_rename_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    exists: bool,
) -> None:
    lock = tmp_path / "ritebook.lock"
    if exists:
        lock.write_bytes(b"old whole document")
    monkeypatch.setattr(writer_module, "rename_entry", _fail)
    with pytest.raises(InstallationPersistenceError, match="lockfile"):
        FilesystemSyncWriterAdapter().write_lockfile(
            GeneratedStateFile(str(lock), b"new whole document", private=False)
        )
    assert lock.read_bytes() == b"old whole document" if exists else not lock.exists()
    assert set(tmp_path.iterdir()) == ({lock} if exists else set())


def test_sync_writer_lock_failure_keeps_completed_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target"
    writer = FilesystemSyncWriterAdapter()
    writer.replace_tree(
        staged_path=str(_tree(tmp_path / "staged", "new")), target_path=str(target), expected_digest=None
    )
    monkeypatch.setattr(writer_module, "rename_entry", _fail)
    with pytest.raises(InstallationPersistenceError):
        writer.write_lockfile(GeneratedStateFile(str(tmp_path / "ritebook.lock"), b"new", private=False))
    assert (target / "SKILL.md").read_text() == "new"
    assert set(tmp_path.iterdir()) == {target}


@pytest.mark.parametrize("fail_restore", [False, True])
def test_sync_writer_placement_failure_restores_only_current_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fail_restore: bool,
) -> None:
    writer = FilesystemSyncWriterAdapter()
    earlier = tmp_path / "earlier"
    writer.replace_tree(
        staged_path=str(_tree(tmp_path / "first", "first")), target_path=str(earlier), expected_digest=None
    )
    target = _tree(tmp_path / "target", "old")
    staged = _tree(tmp_path / "staged", "new")
    original = writer_module.rename_entry

    def fail_placement(source_fd: int, source: str, destination_fd: int, destination: str) -> None:
        if source == staged.name or (fail_restore and source.endswith(".previous")):
            _fail()
        original(source_fd, source, destination_fd, destination)

    monkeypatch.setattr(writer_module, "rename_entry", fail_placement)
    with pytest.raises(InstallationPersistenceError) as error:
        writer.replace_tree(
            staged_path=str(staged), target_path=str(target), expected_digest=canonical_tree_digest(target)
        )
    assert (earlier / "SKILL.md").read_text() == "first"
    assert (staged / "SKILL.md").read_text() == "new"
    backups = list(tmp_path.glob("*.previous"))
    if fail_restore:
        assert not target.exists()
        assert len(backups) == 1
        assert (backups[0] / "SKILL.md").read_text() == "old"
        assert str(backups[0]) in str(error.value)
        assert "restoration failed" in str(error.value)
    else:
        assert (target / "SKILL.md").read_text() == "old"
        assert backups == []


def test_sync_writer_backup_cleanup_failure_keeps_new_target_and_reports_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _tree(tmp_path / "target", "old")
    staged = _tree(tmp_path / "staged", "new")
    monkeypatch.setattr(writer_module, "remove_entry", _fail)
    with pytest.raises(InstallationPersistenceError, match="clean up prior tree") as error:
        FilesystemSyncWriterAdapter().replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=canonical_tree_digest(target),
        )
    assert (target / "SKILL.md").read_text() == "new"
    [backup] = tmp_path.glob("*.previous")
    assert (backup / "SKILL.md").read_text() == "old"
    assert str(backup) in str(error.value)


def test_sync_writer_temp_cleanup_failure_preserves_primary_failure_and_whole_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock = tmp_path / "ritebook.lock"
    lock.write_bytes(b"old")
    monkeypatch.setattr(writer_module, "rename_entry", _fail)
    monkeypatch.setattr(writer_module, "remove_entry", _fail)
    with pytest.raises(InstallationPersistenceError, match="lockfile write failed") as error:
        FilesystemSyncWriterAdapter().write_lockfile(GeneratedStateFile(str(lock), b"new", private=False))
    assert lock.read_bytes() == b"old"
    [temporary] = tmp_path.glob("*.tmp")
    assert temporary.read_bytes() == b"new"
    assert str(temporary) in str(error.value)


def test_sync_writer_error_after_lock_replacement_keeps_whole_new_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock = tmp_path / "ritebook.lock"
    lock.write_bytes(b"old")
    calls = 0
    original = writer_module.require_directory_identity

    def fail_after_replace(path: Path, descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            _fail()
        original(path, descriptor)

    monkeypatch.setattr(writer_module, "require_directory_identity", fail_after_replace)
    with pytest.raises(InstallationPersistenceError):
        FilesystemSyncWriterAdapter().write_lockfile(
            GeneratedStateFile(str(lock), b"whole new document", private=False)
        )
    assert lock.read_bytes() == b"whole new document"
    assert set(tmp_path.iterdir()) == {lock}


def test_sync_writer_cleanup_error_after_lock_replacement_returns_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock = tmp_path / "ritebook.lock"
    monkeypatch.setattr(writer_module, "entry_metadata", _fail)
    with pytest.raises(InstallationPersistenceError, match="lockfile may already be replaced"):
        FilesystemSyncWriterAdapter().write_lockfile(
            GeneratedStateFile(str(lock), b"new whole document", private=False)
        )
    assert lock.read_bytes() == b"new whole document"
    assert set(tmp_path.iterdir()) == {lock}


def test_sync_writer_post_placement_error_does_not_restore_completed_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _tree(tmp_path / "target", "old")
    staged = _tree(tmp_path / "staged", "new")
    original = writer_module.require_directory_identity
    calls = 0

    def fail_once_after_placement(path: Path, descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            _fail()
        original(path, descriptor)

    monkeypatch.setattr(writer_module, "require_directory_identity", fail_once_after_placement)
    with pytest.raises(InstallationPersistenceError):
        FilesystemSyncWriterAdapter().replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=canonical_tree_digest(target),
        )
    assert (target / "SKILL.md").read_text() == "new"
    assert set(tmp_path.iterdir()) == {target}


def test_sync_writer_rejects_symlink_ancestor_and_special_staged_entry(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(outside, target_is_directory=True)
    staged = _tree(tmp_path / "staged", "new")
    with pytest.raises(UnsafeInstallPathError):
        FilesystemSyncWriterAdapter().replace_tree(
            staged_path=str(staged), target_path=str(alias / "target"), expected_digest=None
        )
    assert list(outside.iterdir()) == []
    (staged / "link").symlink_to(outside)
    with pytest.raises(UnsafeInstallPathError):
        FilesystemSyncWriterAdapter().replace_tree(
            staged_path=str(staged), target_path=str(tmp_path / "target"), expected_digest=None
        )
    assert not (tmp_path / "target").exists()


def _tree(path: Path, text: str) -> Path:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(text)
    return path


def _fail(*_args: object, **_kwargs: object) -> None:
    msg = "injected I/O failure"
    raise OSError(msg)
