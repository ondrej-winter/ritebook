"""Filesystem adapter for local index registry metadata."""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import AbstractContextManager, contextmanager, suppress
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, cast

from ritebook.features.index_registry.application.dtos import (
    AliasOrigin,
    IndexSourceType,
    RecoverableIndex,
    RegisteredIndex,
)
from ritebook.features.index_registry.application.errors import (
    IndexRegistryBusyError,
    IndexRegistryPersistenceError,
)
from ritebook.shared_kernel import require_safe_persisted_source

if TYPE_CHECKING:
    from collections.abc import Generator

DEFAULT_REGISTRY_PATH = "~/.config/ritebook/indexes.json"
SCHEMA_VERSION = 2
ROOT_FIELDS = frozenset({"schema_version", "indexes"})
ENTRY_FIELDS = frozenset(
    {
        "name",
        "published_name",
        "alias_origin",
        "source",
        "source_type",
        "source_revision",
        "source_branch",
        "index_digest",
        "source_cache_path",
        "cached_index_path",
        "source_schema_version",
        "skill_count",
        "added_at",
        "updated_at",
    },
)


try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX is required by the current contract.
    fcntl = None  # type: ignore[assignment]


class FilesystemIndexRegistry:
    """Persist registered index metadata in deterministic JSON."""

    def __init__(self, *, lock_timeout_seconds: float = 5.0) -> None:
        """Initialize bounded registry lock acquisition."""
        if lock_timeout_seconds < 0:
            msg = "Index registry lock timeout must not be negative."
            raise ValueError(msg)
        self._lock_timeout_seconds = lock_timeout_seconds

    def get(self, name: str, registry_path: str | None) -> RegisteredIndex | None:
        """Return a registered index by name when present."""
        with self._read_transaction(registry_path) as transaction:
            return transaction.get(name)

    def list(self, registry_path: str | None) -> tuple[RegisteredIndex, ...]:
        """Return all registered indexes in deterministic name order."""
        with self._read_transaction(registry_path) as transaction:
            return transaction.list()

    def upsert(self, entry: RegisteredIndex, registry_path: str | None) -> None:
        """Insert or replace a registry entry and write the registry file."""
        with self.write_transaction(registry_path) as transaction:
            transaction.upsert(entry)

    def write_transaction(
        self,
        registry_path: str | None,
    ) -> AbstractContextManager[_FilesystemIndexRegistryTransaction]:
        """Open one bounded exclusive registry transaction."""
        return self._transaction(registry_path, exclusive=True)

    @contextmanager
    def recovery_transaction(
        self,
        registry_path: str | None,
    ) -> Generator[_FilesystemIndexRegistryTransaction | _LegacyRegistryTransaction]:
        """Allow explicit rebuilding of schema-v1 source registrations under lock."""
        path = _registry_path(registry_path)
        lock = _acquire_lock(
            _lock_path(path),
            exclusive=True,
            timeout_seconds=self._lock_timeout_seconds,
        )
        try:
            payload = _load_payload(path, allow_legacy=True)
            if payload["schema_version"] == 1:
                transaction = _LegacyRegistryTransaction(path=path, payload=payload)
                yield transaction
                if not transaction.list():
                    _write_entries(path, {})
            else:
                yield _FilesystemIndexRegistryTransaction(path=path, entries=_parse_entries(payload, path))
        finally:
            _release_lock(lock)

    def _read_transaction(
        self,
        registry_path: str | None,
    ) -> AbstractContextManager[_FilesystemIndexRegistryTransaction]:
        return self._transaction(registry_path, exclusive=False)

    @contextmanager
    def _transaction(
        self,
        registry_path: str | None,
        *,
        exclusive: bool,
    ) -> Generator[_FilesystemIndexRegistryTransaction]:
        path = _registry_path(registry_path)
        lock = _acquire_lock(
            _lock_path(path),
            exclusive=exclusive,
            timeout_seconds=self._lock_timeout_seconds,
        )
        try:
            yield _FilesystemIndexRegistryTransaction(
                path=path,
                entries=_load_entries(path),
            )
        finally:
            _release_lock(lock)


class _FilesystemIndexRegistryTransaction:
    """Locked registry snapshot used by one reader or writer."""

    def __init__(self, *, path: Path, entries: dict[str, RegisteredIndex]) -> None:
        self._path = path
        self._entries = entries

    def get(self, name: str) -> RegisteredIndex | None:
        """Return an entry from the locked snapshot."""
        return self._entries.get(name)

    def list(self) -> tuple[RegisteredIndex, ...]:
        """Return entries in deterministic alias order."""
        return tuple(self._entries[name] for name in sorted(self._entries))

    def upsert(self, entry: RegisteredIndex) -> None:
        """Atomically replace the registry with one updated entry."""
        previous = self._entries.get(entry.name)
        self._entries[entry.name] = entry
        try:
            _write_entries(self._path, self._entries)
        except BaseException:
            if previous is None:
                del self._entries[entry.name]
            else:
                self._entries[entry.name] = previous
            raise


class _LegacyRegistryTransaction:
    """Retain raw failed registrations until all bindings have been rebuilt."""

    def __init__(self, *, path: Path, payload: dict[str, Any]) -> None:
        self._path = path
        self._raw_entries: dict[str, dict[str, Any]] = {}
        self._entries: dict[str, RegisteredIndex | RecoverableIndex] = {}
        for raw in payload["indexes"]:
            if not isinstance(raw, dict) or not all(
                isinstance(raw.get(key), str) for key in ("name", "source", "source_type")
            ):
                msg = "legacy index registry has malformed source metadata"
                raise IndexRegistryPersistenceError(msg)
            try:
                entry = RecoverableIndex(
                    name=raw["name"],
                    source=raw["source"],
                    source_type=IndexSourceType(raw["source_type"]),
                )
            except (TypeError, ValueError, KeyError) as err:
                msg = "legacy index registry has invalid aliases or unsafe source metadata"
                raise IndexRegistryPersistenceError(msg) from err
            if entry.name in self._entries:
                msg = "legacy index registry contains duplicate aliases"
                raise IndexRegistryPersistenceError(msg)
            self._entries[entry.name] = entry
            self._raw_entries[entry.name] = raw

    def get(self, name: str) -> RegisteredIndex | RecoverableIndex | None:
        """Return the validated binding or source locator."""
        return self._entries.get(name)

    def list(self) -> tuple[RegisteredIndex | RecoverableIndex, ...]:
        """Return every registration in deterministic alias order."""
        return tuple(self._entries[name] for name in sorted(self._entries))

    def upsert(self, entry: RegisteredIndex) -> None:
        """Persist progress without promoting incomplete registrations to schema v2."""
        entries = {**self._entries, entry.name: entry}
        raw_entries = {**self._raw_entries, entry.name: _entry_to_json(entry)}
        version = 1 if any(isinstance(item, RecoverableIndex) for item in entries.values()) else SCHEMA_VERSION
        _write_payload(
            self._path,
            {
                "schema_version": version,
                "indexes": [raw_entries[name] for name in sorted(raw_entries)],
            },
        )
        self._entries = entries
        self._raw_entries = raw_entries


def _registry_path(registry_path: str | None) -> Path:
    return Path(registry_path or DEFAULT_REGISTRY_PATH).expanduser()


def _lock_path(registry_path: Path) -> Path:
    return registry_path.with_name(f"{registry_path.name}.lock")


def _acquire_lock(
    path: Path,
    *,
    exclusive: bool,
    timeout_seconds: float,
) -> IO[str]:
    if fcntl is None:
        msg = "index registry locking is unavailable on this platform"
        raise IndexRegistryPersistenceError(msg)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.open("a+", encoding="utf-8")
    except OSError as err:
        msg = f"index registry lock cannot be opened: {path}"
        raise IndexRegistryPersistenceError(msg) from err

    operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(lock.fileno(), operation | fcntl.LOCK_NB)
        except BlockingIOError as err:
            if time.monotonic() >= deadline:
                lock.close()
                msg = "another index registry operation is already running"
                raise IndexRegistryBusyError(msg) from err
            time.sleep(min(0.01, timeout_seconds))
        except OSError as err:
            lock.close()
            msg = f"index registry lock cannot be acquired: {path}"
            raise IndexRegistryPersistenceError(msg) from err
        else:
            return lock


def _release_lock(lock: IO[str]) -> None:
    try:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    finally:
        lock.close()


def _load_entries(path: Path) -> dict[str, RegisteredIndex]:
    return _parse_entries(_load_payload(path), path)


def _load_payload(path: Path, *, allow_legacy: bool = False) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "indexes": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        msg = f"unable to read index registry: {path}"
        raise IndexRegistryPersistenceError(msg) from err
    versions = {1, SCHEMA_VERSION} if allow_legacy else {SCHEMA_VERSION}
    if (
        not isinstance(payload, dict)
        or type(payload.get("schema_version")) is not int
        or payload.get("schema_version") not in versions
    ):
        msg = (
            "index registry requires schema version 2; "
            f"recover schema v1 with ritebook indexes update --all --force: {path}"
        )
        raise IndexRegistryPersistenceError(msg)
    if set(payload) != ROOT_FIELDS:
        msg = f"index registry root is malformed: {path}"
        raise IndexRegistryPersistenceError(msg)
    raw_entries = payload.get("indexes", [])
    if not isinstance(raw_entries, list):
        msg = f"index registry indexes must be an array: {path}"
        raise IndexRegistryPersistenceError(msg)
    return payload


def _parse_entries(payload: dict[str, Any], path: Path) -> dict[str, RegisteredIndex]:
    entries: dict[str, RegisteredIndex] = {}
    try:
        for raw_entry in payload["indexes"]:
            entry = _entry_from_json(cast("dict[str, Any]", raw_entry))
            entries[entry.name] = entry
    except (TypeError, ValueError, KeyError) as err:
        msg = f"index registry contains invalid metadata: {path}"
        raise IndexRegistryPersistenceError(msg) from err
    return entries


def _write_entries(path: Path, entries: dict[str, RegisteredIndex]) -> None:
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "indexes": [_entry_to_json(entries[name]) for name in sorted(entries)],
    }
    _write_payload(path, payload)


def _write_payload(path: Path, payload: dict[str, object]) -> None:
    content = json.dumps(payload, indent=2) + "\n"
    temp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _remove_abandoned_temporary_files(path)
        descriptor, temp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temp_path = Path(temp_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temp_path.chmod(0o600)
        temp_path.replace(path)
    except OSError as err:
        msg = f"unable to write index registry: {path}"
        raise IndexRegistryPersistenceError(msg) from err
    finally:
        if temp_path is not None:
            with suppress(OSError):
                temp_path.unlink(missing_ok=True)


def _remove_abandoned_temporary_files(path: Path) -> None:
    pattern = f".{path.name}.*.tmp"
    for temporary_path in path.parent.glob(pattern):
        temporary_path.unlink(missing_ok=True)


def _entry_from_json(payload: dict[str, Any]) -> RegisteredIndex:
    if set(payload) != ENTRY_FIELDS:
        msg = "index registry entry is malformed"
        raise IndexRegistryPersistenceError(msg)
    try:
        source_revision = str(payload["source_revision"])
        index_digest = str(payload["index_digest"])
    except KeyError as err:
        msg = "index registry entry lacks required source provenance; remove and regenerate it with add-index"
        raise IndexRegistryPersistenceError(msg) from err
    source = str(payload["source"])
    source_type = IndexSourceType(str(payload["source_type"]))
    name = str(payload["name"])
    published_name = str(payload["published_name"])
    alias_origin = AliasOrigin(str(payload["alias_origin"]))
    try:
        require_safe_persisted_source(source, source_type.value)
    except ValueError as err:
        msg = "index registry contains an unsafe Git source; remove and regenerate it"
        raise IndexRegistryPersistenceError(msg) from err
    return RegisteredIndex(
        name=name,
        published_name=published_name,
        alias_origin=alias_origin,
        source=source,
        source_type=source_type,
        source_revision=source_revision,
        source_branch=str(payload["source_branch"]),
        index_digest=index_digest,
        source_cache_path=cast("str | None", payload.get("source_cache_path")),
        cached_index_path=str(payload["cached_index_path"]),
        source_schema_version=int(payload["source_schema_version"]),
        skill_count=int(payload["skill_count"]),
        added_at=str(payload["added_at"]),
        updated_at=str(payload["updated_at"]),
    )


def _entry_to_json(entry: RegisteredIndex) -> dict[str, Any]:
    try:
        require_safe_persisted_source(entry.source, entry.source_type.value)
    except ValueError as err:
        msg = "refusing to persist an unsafe Git source"
        raise IndexRegistryPersistenceError(msg) from err
    return {
        "name": entry.name,
        "published_name": entry.published_name,
        "alias_origin": entry.alias_origin.value,
        "source": entry.source,
        "source_type": entry.source_type.value,
        "source_revision": entry.source_revision,
        "source_branch": entry.source_branch,
        "index_digest": entry.index_digest,
        "source_cache_path": entry.source_cache_path,
        "cached_index_path": entry.cached_index_path,
        "source_schema_version": entry.source_schema_version,
        "skill_count": entry.skill_count,
        "added_at": entry.added_at,
        "updated_at": entry.updated_at,
    }
