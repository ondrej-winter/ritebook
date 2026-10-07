import json
from pathlib import Path

import pytest

from ritebook.features.skill_installation.adapters.outbound import (
    FilesystemInstallationTransactionAdapter,
    installation_transaction,
)
from ritebook.features.skill_installation.application.dtos import GeneratedStateFile
from ritebook.features.skill_installation.application.errors import (
    InstallationBusyError,
    InstallationPersistenceError,
    UnsafeInstallPathError,
)


def test_installation_transaction_refuses_concurrent_operation(tmp_path: Path) -> None:
    adapter = FilesystemInstallationTransactionAdapter(lock_timeout_seconds=0.01)
    lock_path = tmp_path / "state" / "install.lock"
    journal_path = tmp_path / "state" / "transaction.json"

    with (
        adapter.open(lock_path=str(lock_path), journal_path=str(journal_path)),
        pytest.raises(InstallationBusyError, match="another installation"),
    ):
        _open_and_close(adapter, lock_path=lock_path, journal_path=journal_path)


def test_installation_transaction_rolls_back_uncommitted_replacement(
    tmp_path: Path,
) -> None:
    adapter = FilesystemInstallationTransactionAdapter()
    target = tmp_path / "skills" / "code-review"
    staged = tmp_path / "candidate"
    target.mkdir(parents=True)
    staged.mkdir()
    (target / "SKILL.md").write_text("old\n", encoding="utf-8")
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="injected"):
        _replace_then_fail(
            adapter,
            lock_path=tmp_path / "state" / "install.lock",
            journal_path=tmp_path / "state" / "transaction.json",
            staged=staged,
            target=target,
        )

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "old\n"
    assert not (tmp_path / "state" / "transaction.json").exists()


def test_installation_transaction_commits_target_and_multiple_state_files(
    tmp_path: Path,
) -> None:
    adapter = FilesystemInstallationTransactionAdapter()
    target = tmp_path / "skills" / "code-review"
    staged = tmp_path / "candidate"
    staged.mkdir()
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")
    lockfile = tmp_path / "ritebook.lock"
    ownership = tmp_path / ".ritebook" / "installations.json"

    with adapter.open(
        lock_path=str(tmp_path / ".ritebook" / "install.lock"),
        journal_path=str(tmp_path / ".ritebook" / "transaction.json"),
    ) as transaction:
        transaction.replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=None,
        )
        transaction.commit_state(
            (
                GeneratedStateFile(
                    path=str(lockfile),
                    content=b'{"schema_version":2}\n',
                    private=False,
                ),
                GeneratedStateFile(
                    path=str(ownership),
                    content=b'{"schema_version":2,"installations":[]}\n',
                    private=True,
                ),
            ),
        )

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "new\n"
    assert lockfile.read_bytes() == b'{"schema_version":2}\n'
    assert ownership.read_bytes() == b'{"schema_version":2,"installations":[]}\n'
    assert not (tmp_path / ".ritebook" / "transaction.json").exists()


def test_installation_transaction_rolls_back_target_and_state_write_failure(
    tmp_path: Path,
) -> None:
    target = tmp_path / "skills" / "code-review"
    staged = tmp_path / "candidate"
    target.mkdir(parents=True)
    staged.mkdir()
    (target / "SKILL.md").write_text("old\n", encoding="utf-8")
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")
    lockfile = tmp_path / "ritebook.lock"
    ownership = tmp_path / ".ritebook" / "installations.json"
    lockfile.write_text("old-lock\n", encoding="utf-8")
    ownership.parent.mkdir()
    ownership.write_text("old-ownership\n", encoding="utf-8")
    failed = False

    def fail_second_state_write(
        path: Path,
        content: bytes,
        *,
        private: bool,
    ) -> None:
        nonlocal failed
        if path == ownership and not failed:
            failed = True
            message = "injected state failure"
            raise OSError(message)
        _write_file(path, content, private=private)

    adapter = FilesystemInstallationTransactionAdapter(
        state_writer=fail_second_state_write,
    )

    with pytest.raises(
        InstallationPersistenceError,
        match="generated installation state",
    ):
        _replace_and_commit(
            adapter,
            lock_path=tmp_path / ".ritebook" / "install.lock",
            journal_path=tmp_path / ".ritebook" / "transaction.json",
            staged=staged,
            target=target,
            files=(
                GeneratedStateFile(
                    path=str(lockfile),
                    content=b"new-lock\n",
                    private=False,
                ),
                GeneratedStateFile(
                    path=str(ownership),
                    content=b"new-ownership\n",
                    private=True,
                ),
            ),
        )

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "old\n"
    assert lockfile.read_text(encoding="utf-8") == "old-lock\n"
    assert ownership.read_text(encoding="utf-8") == "old-ownership\n"


def test_installation_transaction_rolls_back_when_state_parent_is_file(
    tmp_path: Path,
) -> None:
    adapter = FilesystemInstallationTransactionAdapter()
    target = tmp_path / "skills" / "code-review"
    staged = tmp_path / "candidate"
    staged.mkdir()
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(
        InstallationPersistenceError,
        match="generated installation state",
    ):
        _replace_and_commit(
            adapter,
            lock_path=tmp_path / ".ritebook" / "install.lock",
            journal_path=tmp_path / ".ritebook" / "transaction.json",
            staged=staged,
            target=target,
            files=(
                GeneratedStateFile(
                    path=str(blocked_parent / "ritebook.lock"),
                    content=b"new-lock\n",
                    private=False,
                ),
            ),
        )

    assert not target.exists()
    assert blocked_parent.read_text(encoding="utf-8") == "not a directory\n"
    assert not (tmp_path / ".ritebook" / "transaction.json").exists()


def test_transaction_rejects_symlink_ancestor_race_without_touching_outside(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = FilesystemInstallationTransactionAdapter()
    target_root = tmp_path / "targets"
    target_parent = target_root / "skills"
    target_parent.mkdir(parents=True)
    displaced_root = tmp_path / "displaced-targets"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = target_parent / "code-review"
    staged = tmp_path / "candidate"
    staged.mkdir()
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")

    with adapter.open(
        lock_path=str(tmp_path / ".ritebook" / "install.lock"),
        journal_path=str(tmp_path / ".ritebook" / "transaction.json"),
    ) as transaction:
        write_journal = transaction._write_journal  # noqa: SLF001

        def replace_ancestor_after_validation() -> None:
            write_journal()
            target_root.rename(displaced_root)
            target_root.symlink_to(outside, target_is_directory=True)

        monkeypatch.setattr(
            transaction,
            "_write_journal",
            replace_ancestor_after_validation,
        )

        with pytest.raises(UnsafeInstallPathError, match=r"symlink|safely"):
            transaction.replace_tree(
                staged_path=str(staged),
                target_path=str(target),
                expected_digest=None,
            )
        target_root.unlink()
        displaced_root.rename(target_root)

    assert list(outside.iterdir()) == []
    assert staged.is_dir()


def test_transaction_rejects_ancestor_swap_after_target_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = FilesystemInstallationTransactionAdapter()
    target_root = tmp_path / "targets"
    target_parent = target_root / "skills"
    target_parent.mkdir(parents=True)
    displaced_root = tmp_path / "displaced-targets"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = target_parent / "code-review"
    staged = tmp_path / "candidate"
    staged.mkdir()
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")
    state_root = tmp_path / ".ritebook"
    journal_path = state_root / "transaction.json"
    rename_entry = installation_transaction.adapter.rename_entry

    def swap_ancestor_after_rename(
        source_parent_fd: int,
        source_name: str,
        destination_parent_fd: int,
        destination_name: str,
    ) -> None:
        rename_entry(
            source_parent_fd,
            source_name,
            destination_parent_fd,
            destination_name,
        )
        if destination_name == target.name:
            target_root.rename(displaced_root)
            target_root.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(
        installation_transaction.adapter,
        "rename_entry",
        swap_ancestor_after_rename,
    )

    with (
        pytest.raises(InstallationPersistenceError, match="rollback failed"),
        adapter.open(
            lock_path=str(state_root / "install.lock"),
            journal_path=str(journal_path),
        ) as transaction,
    ):
        transaction.replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=None,
        )

    assert list(outside.iterdir()) == []
    assert journal_path.is_file()
    assert (displaced_root / "skills" / "code-review" / "SKILL.md").read_text(
        encoding="utf-8",
    ) == "new\n"


def test_transaction_rejects_ancestor_swap_before_state_commit(
    tmp_path: Path,
) -> None:
    adapter = FilesystemInstallationTransactionAdapter()
    target_root = tmp_path / "targets"
    target = target_root / "skills" / "code-review"
    staged = tmp_path / "candidate"
    staged.mkdir()
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")
    state_root = tmp_path / ".ritebook"
    journal_path = state_root / "transaction.json"
    lockfile = tmp_path / "ritebook.lock"
    displaced_root = tmp_path / "displaced-targets"
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(InstallationPersistenceError, match="rollback failed"):
        _replace_swap_ancestor_then_commit(
            adapter,
            lock_path=state_root / "install.lock",
            journal_path=journal_path,
            staged=staged,
            target=target,
            target_root=target_root,
            displaced_root=displaced_root,
            outside=outside,
            state_file=GeneratedStateFile(
                path=str(lockfile),
                content=b"new-lock\n",
                private=False,
            ),
        )

    assert list(outside.iterdir()) == []
    assert not lockfile.exists()
    assert journal_path.is_file()
    assert (displaced_root / "skills" / "code-review" / "SKILL.md").read_text(
        encoding="utf-8",
    ) == "new\n"


def test_transaction_rollback_rejects_symlink_ancestor_and_retains_evidence(
    tmp_path: Path,
) -> None:
    adapter = FilesystemInstallationTransactionAdapter()
    target_root = tmp_path / "targets"
    target = target_root / "skills" / "code-review"
    staged = tmp_path / "candidate"
    target.mkdir(parents=True)
    staged.mkdir()
    (target / "SKILL.md").write_text("old\n", encoding="utf-8")
    (staged / "SKILL.md").write_text("new\n", encoding="utf-8")
    state_root = tmp_path / ".ritebook"
    journal_path = state_root / "transaction.json"
    displaced_root = tmp_path / "displaced-targets"
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(InstallationPersistenceError, match="rollback failed"):
        _replace_swap_ancestor_then_fail(
            adapter,
            lock_path=state_root / "install.lock",
            journal_path=journal_path,
            staged=staged,
            target=target,
            target_root=target_root,
            displaced_root=displaced_root,
            outside=outside,
        )

    assert list(outside.iterdir()) == []
    assert journal_path.is_file()
    assert (displaced_root / "skills" / "code-review" / "SKILL.md").read_text(
        encoding="utf-8",
    ) == "new\n"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    backup = Path(journal["mutations"][0]["backup_path"])
    retained_backup = displaced_root / "skills" / backup.name
    assert (retained_backup / "SKILL.md").read_text(encoding="utf-8") == "old\n"


def test_transaction_recovery_rejects_symlink_ancestor_and_retains_evidence(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / ".ritebook"
    transaction_root = state_root / "transactions" / "txn-1"
    backup = transaction_root / "targets" / "0" / "previous"
    backup.mkdir(parents=True)
    (backup / "SKILL.md").write_text("old\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    target_root = tmp_path / "targets"
    target_root.symlink_to(outside, target_is_directory=True)
    target = target_root / "skills" / "code-review"
    journal_path = state_root / "transaction.json"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "transaction_id": "txn-1",
                "phase": "targets_applied",
                "transaction_root": str(transaction_root),
                "mutations": [
                    {
                        "kind": "replace",
                        "target_path": str(target),
                        "backup_path": str(backup),
                        "had_prior": True,
                    },
                ],
                "state_files": [],
            },
        ),
        encoding="utf-8",
    )

    with (
        pytest.raises(
            InstallationPersistenceError,
            match="interrupted installation recovery failed",
        ),
        FilesystemInstallationTransactionAdapter().open(
            lock_path=str(state_root / "install.lock"),
            journal_path=str(journal_path),
        ),
    ):
        pass

    assert list(outside.iterdir()) == []
    assert journal_path.is_file()
    assert (backup / "SKILL.md").read_text(encoding="utf-8") == "old\n"


def test_installation_transaction_recovers_interrupted_uncommitted_mutation(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / ".ritebook"
    transaction_root = state_root / "transactions" / "txn-1"
    target = tmp_path / "skills" / "code-review"
    backup = transaction_root / "targets" / "0" / "previous"
    target.mkdir(parents=True)
    backup.mkdir(parents=True)
    (target / "SKILL.md").write_text("new\n", encoding="utf-8")
    (backup / "SKILL.md").write_text("old\n", encoding="utf-8")
    journal_path = state_root / "transaction.json"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "transaction_id": "txn-1",
                "phase": "targets_applied",
                "transaction_root": str(transaction_root),
                "mutations": [
                    {
                        "kind": "replace",
                        "target_path": str(target),
                        "backup_path": str(backup),
                        "had_prior": True,
                    },
                ],
                "state_files": [],
            },
        ),
        encoding="utf-8",
    )

    adapter = FilesystemInstallationTransactionAdapter()
    with adapter.open(
        lock_path=str(state_root / "install.lock"),
        journal_path=str(journal_path),
    ):
        pass

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "old\n"
    assert not journal_path.exists()
    assert not transaction_root.exists()


def test_installation_transaction_finalizes_interrupted_committed_state(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / ".ritebook"
    transaction_root = state_root / "transactions" / "txn-1"
    target = tmp_path / "skills" / "code-review"
    backup = transaction_root / "targets" / "0" / "previous"
    lockfile = tmp_path / "ritebook.lock"
    candidate = b'{"schema_version":2}\n'
    target.mkdir(parents=True)
    backup.mkdir(parents=True)
    (target / "SKILL.md").write_text("new\n", encoding="utf-8")
    (backup / "SKILL.md").write_text("old\n", encoding="utf-8")
    lockfile.write_bytes(candidate)
    journal_path = state_root / "transaction.json"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "transaction_id": "txn-1",
                "phase": "state_committed",
                "transaction_root": str(transaction_root),
                "mutations": [
                    {
                        "kind": "replace",
                        "target_path": str(target),
                        "backup_path": str(backup),
                        "had_prior": True,
                    },
                ],
                "state_files": [
                    {
                        "path": str(lockfile),
                        "backup_path": str(transaction_root / "state/0/previous"),
                        "had_prior": False,
                        "candidate_digest": _digest(candidate),
                        "private": False,
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    adapter = FilesystemInstallationTransactionAdapter()
    with adapter.open(
        lock_path=str(state_root / "install.lock"),
        journal_path=str(journal_path),
    ):
        pass

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "new\n"
    assert lockfile.read_bytes() == candidate
    assert not journal_path.exists()
    assert not transaction_root.exists()


def _open_and_close(
    adapter: FilesystemInstallationTransactionAdapter,
    *,
    lock_path: Path,
    journal_path: Path,
) -> None:
    with adapter.open(lock_path=str(lock_path), journal_path=str(journal_path)):
        pass


def _replace_then_fail(
    adapter: FilesystemInstallationTransactionAdapter,
    *,
    lock_path: Path,
    journal_path: Path,
    staged: Path,
    target: Path,
) -> None:
    with adapter.open(
        lock_path=str(lock_path),
        journal_path=str(journal_path),
    ) as transaction:
        transaction.replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=(
                transaction.tree_digest(str(target)) if target.exists() else None
            ),
        )
        message = "injected"
        raise RuntimeError(message)


def _replace_and_commit(
    adapter: FilesystemInstallationTransactionAdapter,
    *,
    lock_path: Path,
    journal_path: Path,
    staged: Path,
    target: Path,
    files: tuple[GeneratedStateFile, ...],
) -> None:
    with adapter.open(
        lock_path=str(lock_path),
        journal_path=str(journal_path),
    ) as transaction:
        transaction.replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=(
                transaction.tree_digest(str(target)) if target.exists() else None
            ),
        )
        transaction.commit_state(files)


def _replace_swap_ancestor_then_fail(
    adapter: FilesystemInstallationTransactionAdapter,
    *,
    lock_path: Path,
    journal_path: Path,
    staged: Path,
    target: Path,
    target_root: Path,
    displaced_root: Path,
    outside: Path,
) -> None:
    with adapter.open(
        lock_path=str(lock_path),
        journal_path=str(journal_path),
    ) as transaction:
        transaction.replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=transaction.tree_digest(str(target)),
        )
        target_root.rename(displaced_root)
        target_root.symlink_to(outside, target_is_directory=True)
        message = "injected"
        raise RuntimeError(message)


def _replace_swap_ancestor_then_commit(
    adapter: FilesystemInstallationTransactionAdapter,
    *,
    lock_path: Path,
    journal_path: Path,
    staged: Path,
    target: Path,
    target_root: Path,
    displaced_root: Path,
    outside: Path,
    state_file: GeneratedStateFile,
) -> None:
    with adapter.open(
        lock_path=str(lock_path),
        journal_path=str(journal_path),
    ) as transaction:
        transaction.replace_tree(
            staged_path=str(staged),
            target_path=str(target),
            expected_digest=None,
        )
        target_root.rename(displaced_root)
        target_root.symlink_to(outside, target_is_directory=True)
        transaction.commit_state((state_file,))


def _write_file(path: Path, content: bytes, *, private: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    if private:
        path.chmod(0o600)


def _digest(content: bytes) -> str:
    import hashlib  # noqa: PLC0415

    return f"sha256:{hashlib.sha256(content).hexdigest()}"
