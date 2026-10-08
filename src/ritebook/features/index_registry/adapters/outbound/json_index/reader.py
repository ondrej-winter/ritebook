"""Read and validate ritebook-index.json publisher indexes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ritebook.features.index_registry.application.dtos import (
    CachedSkillSummary,
    PublishedIndex,
)
from ritebook.features.index_registry.application.errors import (
    InvalidPublishedIndexError,
)
from ritebook.shared_kernel import (
    SchemaV1Catalog,
    SchemaV1CatalogError,
    parse_schema_v1_catalog_bytes,
)

CANONICAL_INDEX_FILENAME = "ritebook-index.json"


class JsonIndexReader:
    """Read published index metadata and cached skill summaries from JSON."""

    def read_index(self, content: bytes) -> PublishedIndex:
        """Validate exact committed root ritebook-index.json bytes."""
        catalog = _parse_catalog(content)
        return PublishedIndex(
            published_name=catalog.published_name,
            schema_version=catalog.schema_version,
            skill_count=len(catalog.skills),
            cacheable_content=content,
            index_digest=_digest(content),
        )

    def read_skills(
        self,
        cached_index_path: str,
        index_digest: str,
    ) -> tuple[CachedSkillSummary, ...]:
        """Verify exact cached bytes before parsing validated skill summaries."""
        content = _read_cached_bytes(Path(cached_index_path))
        if _digest(content) != index_digest:
            msg = (
                "cached ritebook-index.json digest does not match registered "
                "index_digest"
            )
            raise InvalidPublishedIndexError(msg)
        return _cached_skills(_parse_catalog(content))


def _read_cached_bytes(index_path: Path) -> bytes:
    try:
        return index_path.read_bytes()
    except FileNotFoundError as err:
        msg = "cached ritebook-index.json was not found"
        raise InvalidPublishedIndexError(msg) from err
    except OSError as err:
        msg = "unable to read cached ritebook-index.json"
        raise InvalidPublishedIndexError(msg) from err


def _parse_catalog(content: bytes) -> SchemaV1Catalog:
    try:
        return parse_schema_v1_catalog_bytes(content)
    except SchemaV1CatalogError as err:
        message = str(err)
        if message.startswith("invalid schema-v1 catalog structure:"):
            message = (
                f"{message} Reorganize skills into root or collection/skill paths "
                "and republish the index."
            )
        raise InvalidPublishedIndexError(message) from err


def _cached_skills(catalog: SchemaV1Catalog) -> tuple[CachedSkillSummary, ...]:
    return tuple(
        CachedSkillSummary(
            name=skill.name,
            path=skill.path,
            skill_file=skill.skill_file,
            description=skill.description,
            source_root=catalog.skills_root,
        )
        for skill in catalog.skills
    )


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"
