"""Filesystem implementation of publisher skill discovery."""

from collections.abc import Mapping
from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    DiscoveredSkillFile,
    FrontmatterParseError,
    discover_skill_files,
    parse_yaml_frontmatter,
)
from ritebook.features.publisher.domain import SkillEntry


class FilesystemSkillDiscovery:
    """Discover skill entries from directories containing ``SKILL.md`` files."""

    def discover_skills(self, skills_root: str) -> tuple[SkillEntry, ...]:
        """Discover non-hidden skill directories below the explicit skills root."""
        entries = [
            _skill_entry(discovered)
            for discovered in discover_skill_files(Path(skills_root))
        ]
        return tuple(sorted(entries, key=lambda entry: entry.path))


def _skill_entry(discovered: DiscoveredSkillFile) -> SkillEntry:
    skill_dir = discovered.path.parent
    return SkillEntry(
        name=skill_dir.name,
        path=discovered.relative_skill_dir,
        skill_file=discovered.relative_skill_file,
        title=_extract_header_name(discovered.path),
    )


def _extract_header_name(skill_file: Path) -> str | None:
    frontmatter = parse_yaml_frontmatter(skill_file)
    if isinstance(frontmatter, FrontmatterParseError):
        return None
    if not isinstance(frontmatter, Mapping):
        return None

    name = frontmatter.get("name")
    if not isinstance(name, str):
        return None

    title = name.strip()
    if title:
        return title
    return None
