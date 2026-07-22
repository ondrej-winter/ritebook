from ritebook.features.index_registry.application.dtos import (
    CachedSkillSummary,
    IndexSourceType,
    PreparedIndexSource,
    PublishedIndex,
    RegisteredIndex,
)

SOURCE_REVISION = "a" * 40
UPDATED_SOURCE_REVISION = "c" * 40
INDEX_DIGEST = f"sha256:{'b' * 64}"


class FakeGitSource:
    def __init__(self, prepared: PreparedIndexSource | None = None) -> None:
        self.prepared = prepared or PreparedIndexSource(
            source="git@example.com:company/skills.git",
            source_type=IndexSourceType.GIT_URL,
            repository_path="/cache/git/source-id",
            source_revision=SOURCE_REVISION,
            index_content=b'{"schema_version":1}\n',
            source_cache_path="/cache/git/source-id",
        )
        self.prepare_calls: list[tuple[str, str | None]] = []
        self.refresh_calls: list[tuple[str, str | None, str | None]] = []

    def prepare_source(
        self,
        source: str,
        cache_root: str | None,
    ) -> PreparedIndexSource:
        self.prepare_calls.append((source, cache_root))
        return self.prepared

    def refresh_source(
        self,
        *,
        source: str,
        source_cache_path: str | None,
        cache_root: str | None,
    ) -> PreparedIndexSource:
        self.refresh_calls.append((source, source_cache_path, cache_root))
        if self.prepared.source == "git@example.com:company/skills.git":
            index_name = source.removeprefix("git@example.com:company/").removesuffix(
                ".git",
            )
            return PreparedIndexSource(
                source=source,
                source_type=IndexSourceType.GIT_URL,
                repository_path=f"/cache/git/{index_name}",
                source_revision=UPDATED_SOURCE_REVISION,
                index_content=index_name.encode(),
                source_cache_path=source_cache_path or f"/cache/git/{index_name}",
            )
        return self.prepared


class FakeIndexReader:
    def __init__(
        self,
        published: PublishedIndex | dict[str, PublishedIndex] | None = None,
        failures: dict[str, Exception] | None = None,
    ) -> None:
        self.published = published or PublishedIndex(
            published_name="company-skills",
            schema_version=1,
            skill_count=2,
            cacheable_content='{"schema_version":1}\n',
            index_digest=INDEX_DIGEST,
        )
        self.failures = failures or {}
        self.read_contents: list[bytes] = []

    def read_index(self, content: bytes) -> PublishedIndex:
        self.read_contents.append(content)
        index_name = content.decode()
        if index_name in self.failures:
            raise self.failures[index_name]
        if isinstance(self.published, dict):
            return self.published[index_name]
        return self.published


class FailingIndexReader:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def read_index(self, _content: bytes) -> PublishedIndex:
        raise self.error


class FakeCachedIndexReader:
    def __init__(
        self,
        skills_by_path: dict[str, tuple[CachedSkillSummary, ...]] | None = None,
    ) -> None:
        self.skills_by_path = skills_by_path or {}
        self.read_paths: list[str] = []

    def read_skills(self, cached_index_path: str) -> tuple[CachedSkillSummary, ...]:
        self.read_paths.append(cached_index_path)
        return self.skills_by_path.get(cached_index_path, ())


class FakeRegistry:
    def __init__(
        self,
        entries: list[RegisteredIndex] | None = None,
        *,
        upsert_error: Exception | None = None,
    ) -> None:
        self.entries = {entry.name: entry for entry in entries or []}
        self.upsert_error = upsert_error
        self.get_calls: list[tuple[str, str | None]] = []
        self.list_calls: list[str | None] = []
        self.upsert_calls: list[tuple[RegisteredIndex, str | None]] = []

    def get(self, name: str, registry_path: str | None) -> RegisteredIndex | None:
        self.get_calls.append((name, registry_path))
        return self.entries.get(name)

    def upsert(self, entry: RegisteredIndex, registry_path: str | None) -> None:
        if self.upsert_error is not None:
            raise self.upsert_error
        self.entries[entry.name] = entry
        self.upsert_calls.append((entry, registry_path))

    def list(self, registry_path: str | None) -> tuple[RegisteredIndex, ...]:
        self.list_calls.append(registry_path)
        return tuple(self.entries[name] for name in sorted(self.entries))


class FakeCache:
    def __init__(self) -> None:
        self.write_calls: list[tuple[str, str, str, str | None, str | None]] = []
        self.discard_calls: list[tuple[str, str, str | None]] = []

    def cached_index_path(
        self,
        *,
        name: str,
        index_digest: str,
        cache_root: str | None,
    ) -> str:
        digest = index_digest.removeprefix("sha256:")
        return f"{cache_root or '/cache'}/indexes/{name}/{digest}/ritebook-index.json"

    def write_index(
        self,
        *,
        name: str,
        content: str,
        index_digest: str,
        cache_root: str | None,
        preserve_path: str | None,
    ) -> str:
        self.write_calls.append(
            (name, content, index_digest, cache_root, preserve_path),
        )
        return self.cached_index_path(
            name=name,
            index_digest=index_digest,
            cache_root=cache_root,
        )

    def discard_index(
        self,
        *,
        name: str,
        cached_index_path: str,
        cache_root: str | None,
    ) -> None:
        self.discard_calls.append((name, cached_index_path, cache_root))


def registered_index(
    *,
    name: str = "company-skills",
    published_name: str = "company-skills",
    source: str = "git@example.com:company/skills.git",
    source_type: IndexSourceType = IndexSourceType.GIT_URL,
    source_cache_path: str | None = "/cache/git/source-id",
    source_revision: str = SOURCE_REVISION,
    index_digest: str = INDEX_DIGEST,
    cached_index_path: str = "/cache/indexes/company-skills/ritebook-index.json",
    source_schema_version: int = 1,
    skill_count: int = 2,
    added_at: str = "2026-07-08T18:00:00Z",
    updated_at: str = "2026-07-08T18:00:00Z",
) -> RegisteredIndex:
    return RegisteredIndex(
        name=name,
        published_name=published_name,
        source=source,
        source_type=source_type,
        source_revision=source_revision,
        index_digest=index_digest,
        source_cache_path=source_cache_path,
        cached_index_path=cached_index_path,
        source_schema_version=source_schema_version,
        skill_count=skill_count,
        added_at=added_at,
        updated_at=updated_at,
    )
