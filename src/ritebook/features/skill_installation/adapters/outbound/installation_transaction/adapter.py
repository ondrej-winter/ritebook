"""Lock, journal, mutate, commit, and recover installation transactions."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from contextlib import AbstractContextManager, contextmanager, suppress
from pathlib import Path
from typing import IO, TYPE_CHECKING, Protocol, cast

from ritebook.features.skill_installation.adapters.outbound.safe_filesystem import (
    absolute_path,
    entry_metadata,
    open_verified_directory,
    remove_entry,
    remove_path,
    rename_entry,
    require_directory_identity,
    same_directory,
    sync_directory_descriptor,
)
from ritebook.features.skill_installation.adapters.outbound.tree_digest import (
    canonical_tree_digest,
    canonical_tree_digest_at,
)
from ritebook.features.skill_installation.application.errors import (
    InstallationBusyError,
    InstallationPersistenceError,
    UnsafeInstallPathError,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from ritebook.features.skill_installation.application.dtos import GeneratedStateFile


class StateWriter(Protocol):
    """Write one generated-state file with explicit privacy semantics."""

    def __call__(self, path: Path, content: bytes, *, private: bool) -> None:
        """Persist one complete state-file candidate."""


try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX is required by the current contract.
    fcntl = None  # type: ignore[assignment]

JOURNAL_SCHEMA_VERSION = 1
JOURNAL_FIELDS = frozenset(
    {
        "schema_version",
        "transaction_id",
        "phase",
        "transaction_root",
        "mutations",
        "state_files",
    },
)
MUTATION_FIELDS = frozenset(
    {"kind", "target_path", "backup_path", "had_prior"},
)
STATE_FILE_FIELDS = frozenset(
    {"path", "backup_path", "had_prior", "candidate_digest", "private"},
)


class FilesystemInstallationTransactionAdapter:
    """Coordinate exclusive, recoverable filesystem installation transactions."""

    def __init__(
        self,
        *,
        lock_timeout_seconds: float = 5.0,
        state_writer: StateWriter | None = None,
    ) -> None:
        """Initialize a bounded exclusive-lock timeout."""
        if lock_timeout_seconds < 0:
            msg = "Installation lock timeout must not be negative."
            raise ValueError(msg)
        self._lock_timeout_seconds = lock_timeout_seconds
        self._state_writer = state_writer or _write_state_file

    def open(
        self,
        *,
        lock_path: str,
        journal_path: str,
    ) -> AbstractContextManager[FilesystemInstallationTransaction]:
        """Acquire the operation lock, recover prior work, and open a transaction."""
        return self._open(lock_path=lock_path, journal_path=journal_path)

    @contextmanager
    def _open(
        self,
        *,
        lock_path: str,
        journal_path: str,
    ) -> Iterator[FilesystemInstallationTransaction]:
        lock = _acquire_lock(
            Path(lock_path),
            timeout_seconds=self._lock_timeout_seconds,
        )
        journal = Path(journal_path)
        try:
            _recover_interrupted_transaction(
                journal,
                state_writer=self._state_writer,
            )
            transaction = FilesystemInstallationTransaction(
                journal_path=journal,
                state_writer=self._state_writer,
            )
            try:
                yield transaction
            except BaseException:
                transaction.rollback()
                raise
            else:
                transaction.finish()
        finally:
            _release_lock(lock)


class FilesystemInstallationTransaction:
    """One locked set of target mutations and generated-state writes."""

    def __init__(self, *, journal_path: Path, state_writer: StateWriter) -> None:
        """Initialize an empty lazy journal."""
        self._journal_path = journal_path
        self._transaction_id = uuid.uuid4().hex
        self._transaction_root = (
            journal_path.parent / "transactions" / self._transaction_id
        )
        self._phase = "prepared"
        self._mutations: list[dict[str, object]] = []
        self._state_files: list[dict[str, object]] = []
        self._verified_directories: dict[Path, int] = {}
        self._state_committed = False
        self._finished = False
        self._state_writer = state_writer

    def tree_digest(self, target: str) -> str:
        """Return the canonical digest of a managed target tree."""
        return canonical_tree_digest(Path(target).expanduser())

    def replace_tree(
        self,
        *,
        staged_path: str,
        target_path: str,
        expected_digest: str | None,
    ) -> None:
        """Replace or create a target while retaining its prior tree for rollback."""
        staged = absolute_path(Path(staged_path))
        target = _require_safe_mutation_target(Path(target_path))
        self.tree_digest(str(staged))
        with (
            open_verified_directory(
                target.parent,
                create=True,
                label=f"target parent for {target}",
            ) as target_parent_fd,
            open_verified_directory(
                staged.parent,
                create=False,
                label=f"staging parent for {staged}",
            ) as staged_parent_fd,
        ):
            canonical_tree_digest_at(
                staged_parent_fd,
                staged.name,
                display_path=staged,
            )
            exists = entry_metadata(target_parent_fd, target.name) is not None
            if expected_digest is None:
                if exists:
                    msg = f"target {target} exists without verified Ritebook ownership"
                    raise UnsafeInstallPathError(msg)
            else:
                if not exists:
                    msg = f"owned target is missing: {target}"
                    raise InstallationPersistenceError(msg)
                if (
                    canonical_tree_digest_at(
                        target_parent_fd,
                        target.name,
                        display_path=target,
                    )
                    != expected_digest
                ):
                    msg = f"owned target has local changes: {target}"
                    raise InstallationPersistenceError(msg)

            backup = target.parent / (
                f".{target.name}.ritebook-{self._transaction_id}.previous"
            )
            mutation: dict[str, object] = {
                "kind": "replace",
                "target_path": str(target),
                "backup_path": str(backup),
                "had_prior": exists,
            }
            self._mutations.append(mutation)
            self._phase = "targets_applied"
            self._write_journal()
            require_directory_identity(target.parent, target_parent_fd)
            require_directory_identity(staged.parent, staged_parent_fd)
            try:
                if exists:
                    rename_entry(
                        target_parent_fd,
                        target.name,
                        target_parent_fd,
                        backup.name,
                    )
                    sync_directory_descriptor(target_parent_fd)
                rename_entry(
                    staged_parent_fd,
                    staged.name,
                    target_parent_fd,
                    target.name,
                )
                sync_directory_descriptor(target_parent_fd)
                if not same_directory(staged_parent_fd, target_parent_fd):
                    sync_directory_descriptor(staged_parent_fd)
                require_directory_identity(target.parent, target_parent_fd)
                require_directory_identity(staged.parent, staged_parent_fd)
                self._remember_directory(target.parent, target_parent_fd)
            except OSError as err:
                msg = f"unable to replace installation target: {target}"
                raise InstallationPersistenceError(msg) from err

    def remove_tree(self, *, target_path: str, expected_digest: str) -> None:
        """Remove an unchanged owned target while retaining it for rollback."""
        target = _require_safe_mutation_target(Path(target_path))
        with open_verified_directory(
            target.parent,
            create=False,
            label=f"target parent for {target}",
        ) as target_parent_fd:
            if (
                canonical_tree_digest_at(
                    target_parent_fd,
                    target.name,
                    display_path=target,
                )
                != expected_digest
            ):
                msg = f"owned target has local changes: {target}"
                raise InstallationPersistenceError(msg)
            backup = target.parent / (
                f".{target.name}.ritebook-{self._transaction_id}.previous"
            )
            self._mutations.append(
                {
                    "kind": "remove",
                    "target_path": str(target),
                    "backup_path": str(backup),
                    "had_prior": True,
                },
            )
            self._phase = "targets_applied"
            self._write_journal()
            require_directory_identity(target.parent, target_parent_fd)
            try:
                rename_entry(
                    target_parent_fd,
                    target.name,
                    target_parent_fd,
                    backup.name,
                )
                sync_directory_descriptor(target_parent_fd)
                require_directory_identity(target.parent, target_parent_fd)
                self._remember_directory(target.parent, target_parent_fd)
            except OSError as err:
                msg = f"unable to remove installation target: {target}"
                raise InstallationPersistenceError(msg) from err

    def commit_state(self, files: tuple[GeneratedStateFile, ...]) -> None:
        """Commit all generated-state candidates or restore all prior state."""
        if self._state_committed:
            msg = "Generated installation state was already committed."
            raise InstallationPersistenceError(msg)
        self._verify_remembered_directories()
        _require_expected_state(files)
        self._prepare_state_backups(files)
        self._write_journal()
        try:
            for state_file in files:
                self._state_writer(
                    Path(state_file.path),
                    state_file.content,
                    private=state_file.private,
                )
        except OSError as err:
            msg = "unable to commit generated installation state"
            raise InstallationPersistenceError(msg) from err
        self._verify_remembered_directories()
        self._phase = "state_committed"
        self._state_committed = True
        self._write_journal()

    def finish(self) -> None:
        """Finalize committed work or roll back a transaction without state commit."""
        if self._finished:
            return
        if self._mutations and not self._state_committed:
            self.rollback()
            return
        try:
            self._verify_remembered_directories()
            self._cleanup_artifacts()
        finally:
            self._close_verified_directories()
        self._finished = True

    def rollback(self) -> None:
        """Restore prior generated state and targets, retaining evidence on failure."""
        if self._finished:
            return
        try:
            _restore_state_files(
                self._state_files,
                state_writer=self._state_writer,
            )
            _restore_mutations(self._mutations)
            self._cleanup_artifacts()
        except (OSError, InstallationPersistenceError, UnsafeInstallPathError) as err:
            msg = (
                "installation rollback failed; recover using journal "
                f"{self._journal_path} and transaction data {self._transaction_root}"
            )
            raise InstallationPersistenceError(msg) from err
        finally:
            self._close_verified_directories()
        self._finished = True

    def _remember_directory(self, path: Path, descriptor: int) -> None:
        if path not in self._verified_directories:
            self._verified_directories[path] = os.dup(descriptor)

    def _verify_remembered_directories(self) -> None:
        for path, descriptor in self._verified_directories.items():
            require_directory_identity(path, descriptor)

    def _close_verified_directories(self) -> None:
        for descriptor in self._verified_directories.values():
            with suppress(OSError):
                os.close(descriptor)
        self._verified_directories.clear()

    def _prepare_state_backups(self, files: tuple[GeneratedStateFile, ...]) -> None:
        state_root = self._transaction_root / "state"
        for position, state_file in enumerate(files):
            path = Path(state_file.path)
            backup = state_root / str(position) / "previous"
            had_prior = path.exists()
            if had_prior:
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(path.read_bytes())
                _sync_file(backup)
            self._state_files.append(
                {
                    "path": str(path),
                    "backup_path": str(backup),
                    "had_prior": had_prior,
                    "candidate_digest": _bytes_digest(state_file.content),
                    "private": state_file.private,
                },
            )

    def _write_journal(self) -> None:
        document = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "transaction_id": self._transaction_id,
            "phase": self._phase,
            "transaction_root": str(self._transaction_root),
            "mutations": self._mutations,
            "state_files": self._state_files,
        }
        _atomic_write_bytes(
            self._journal_path,
            _json_bytes(document),
            private=True,
        )

    def _cleanup_artifacts(self) -> None:
        for mutation in self._mutations:
            remove_path(
                Path(cast("str", mutation["backup_path"])),
                missing_parent_ok=False,
            )
        remove_path(self._transaction_root)
        self._journal_path.unlink(missing_ok=True)
        _sync_directory(self._journal_path.parent)


def _acquire_lock(path: Path, *, timeout_seconds: float) -> IO[str]:
    if fcntl is None:
        msg = "installation locking is unavailable on this platform"
        raise InstallationPersistenceError(msg)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.open("a+", encoding="utf-8")
    except OSError as err:
        msg = f"installation lock cannot be opened: {path}"
        raise InstallationPersistenceError(msg) from err

    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as err:
            if time.monotonic() >= deadline:
                lock.close()
                msg = "another installation or sync operation is already running"
                raise InstallationBusyError(msg) from err
            time.sleep(min(0.01, timeout_seconds))
        except OSError as err:
            lock.close()
            msg = f"installation lock cannot be acquired: {path}"
            raise InstallationPersistenceError(msg) from err
        else:
            return lock


def _release_lock(lock: IO[str]) -> None:
    if fcntl is not None:
        with suppress(OSError):
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    lock.close()


def _recover_interrupted_transaction(
    journal_path: Path,
    *,
    state_writer: StateWriter,
) -> None:
    if not journal_path.exists():
        return
    document = _read_journal(journal_path)
    state_files = cast("list[dict[str, object]]", document["state_files"])
    mutations = cast("list[dict[str, object]]", document["mutations"])
    transaction_root = Path(cast("str", document["transaction_root"]))
    try:
        if state_files and _candidate_state_is_committed(state_files):
            for mutation in mutations:
                remove_path(
                    Path(cast("str", mutation["backup_path"])),
                    missing_parent_ok=False,
                )
        else:
            _restore_state_files(state_files, state_writer=state_writer)
            _restore_mutations(mutations)
        remove_path(transaction_root)
        journal_path.unlink(missing_ok=True)
        _sync_directory(journal_path.parent)
    except (OSError, InstallationPersistenceError, UnsafeInstallPathError) as err:
        msg = (
            "interrupted installation recovery failed; recover using journal "
            f"{journal_path} and transaction data {transaction_root}"
        )
        raise InstallationPersistenceError(msg) from err


def _read_journal(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        msg = f"installation transaction journal cannot be read: {path}"
        raise InstallationPersistenceError(msg) from err
    if not isinstance(payload, dict) or set(payload) != JOURNAL_FIELDS:
        msg = f"installation transaction journal is malformed: {path}"
        raise InstallationPersistenceError(msg)
    document = cast("dict[str, object]", payload)
    if document["schema_version"] != JOURNAL_SCHEMA_VERSION:
        msg = f"installation transaction journal has unsupported schema: {path}"
        raise InstallationPersistenceError(msg)
    for field_name in ("transaction_id", "phase", "transaction_root"):
        if not isinstance(document[field_name], str) or not document[field_name]:
            msg = f"installation transaction journal is malformed: {path}"
            raise InstallationPersistenceError(msg)
    _validate_journal_entries(document.get("mutations"), MUTATION_FIELDS, path)
    _validate_journal_entries(document.get("state_files"), STATE_FILE_FIELDS, path)
    return document


def _validate_journal_entries(
    value: object,
    required_fields: frozenset[str],
    path: Path,
) -> None:
    if not isinstance(value, list):
        msg = f"installation transaction journal is malformed: {path}"
        raise InstallationPersistenceError(msg)
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != required_fields:
            msg = f"installation transaction journal is malformed: {path}"
            raise InstallationPersistenceError(msg)


def _candidate_state_is_committed(state_files: list[dict[str, object]]) -> bool:
    for state_file in state_files:
        path = Path(cast("str", state_file["path"]))
        try:
            content = path.read_bytes()
        except OSError:
            return False
        if _bytes_digest(content) != state_file["candidate_digest"]:
            return False
    return True


def _restore_state_files(
    state_files: list[dict[str, object]],
    *,
    state_writer: StateWriter,
) -> None:
    for state_file in reversed(state_files):
        path = Path(cast("str", state_file["path"]))
        backup = Path(cast("str", state_file["backup_path"]))
        if state_file["had_prior"] is True:
            state_writer(
                path,
                backup.read_bytes(),
                private=state_file["private"] is True,
            )
        else:
            with suppress(NotADirectoryError):
                path.unlink(missing_ok=True)
            _sync_directory(path.parent)


def _restore_mutations(mutations: list[dict[str, object]]) -> None:
    for mutation in reversed(mutations):
        target = _require_safe_mutation_target(
            Path(cast("str", mutation["target_path"])),
        )
        backup = absolute_path(Path(cast("str", mutation["backup_path"])))
        if mutation["had_prior"] is True:
            _restore_prior_target(target=target, backup=backup)
        else:
            remove_path(target, missing_parent_ok=False)


def _restore_prior_target(*, target: Path, backup: Path) -> None:
    with (
        open_verified_directory(
            target.parent,
            create=False,
            label=f"target parent for {target}",
        ) as target_parent_fd,
        open_verified_directory(
            backup.parent,
            create=False,
            label=f"backup parent for {backup}",
        ) as backup_parent_fd,
    ):
        backup_metadata = entry_metadata(backup_parent_fd, backup.name)
        target_metadata = entry_metadata(target_parent_fd, target.name)
        if backup_metadata is None:
            if target_metadata is None:
                msg = f"prior installation backup is missing: {backup}"
                raise InstallationPersistenceError(msg)
            return

        require_directory_identity(target.parent, target_parent_fd)
        require_directory_identity(backup.parent, backup_parent_fd)
        if target_metadata is not None:
            remove_entry(target_parent_fd, target.name, target_metadata)
            sync_directory_descriptor(target_parent_fd)
        rename_entry(
            backup_parent_fd,
            backup.name,
            target_parent_fd,
            target.name,
        )
        sync_directory_descriptor(target_parent_fd)
        if not same_directory(backup_parent_fd, target_parent_fd):
            sync_directory_descriptor(backup_parent_fd)


def _require_safe_mutation_target(target: Path) -> Path:
    absolute = absolute_path(target)
    if absolute == Path(absolute.anchor):
        msg = f"target {target} resolves to filesystem root"
        raise UnsafeInstallPathError(msg)
    return absolute


def _atomic_write_bytes(path: Path, content: bytes, *, private: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        if private:
            temporary_path.chmod(0o600)
        temporary_path.replace(path)
        _sync_directory(path.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _write_state_file(path: Path, content: bytes, *, private: bool) -> None:
    _atomic_write_bytes(path, content, private=private)


def _json_bytes(document: Mapping[str, object]) -> bytes:
    return f"{json.dumps(document, indent=2, sort_keys=True)}\n".encode()


def _bytes_digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _require_expected_state(files: tuple[GeneratedStateFile, ...]) -> None:
    for state_file in files:
        if state_file.expected_digest is None:
            continue
        path = Path(state_file.path)
        try:
            current = path.read_bytes()
        except OSError as err:
            msg = f"generated installation state changed concurrently: {path}"
            raise InstallationPersistenceError(msg) from err
        if _bytes_digest(current) != state_file.expected_digest:
            msg = f"generated installation state changed concurrently: {path}"
            raise InstallationPersistenceError(msg)


def _sync_file(path: Path) -> None:
    with path.open("rb") as file:
        os.fsync(file.fileno())
    _sync_directory(path.parent)


def _sync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        sync_directory_descriptor(descriptor)
    finally:
        os.close(descriptor)
