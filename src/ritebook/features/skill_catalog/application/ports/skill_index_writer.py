"""Outbound port for writing skill indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_catalog.domain import SkillCatalog


class SkillIndexWriterPort(Protocol):
    """Outbound dependency for writing a skill catalog index."""

    def write_index(self, catalog: SkillCatalog, output_path: str) -> None:
        """Write the supplied catalog to the requested output path."""
