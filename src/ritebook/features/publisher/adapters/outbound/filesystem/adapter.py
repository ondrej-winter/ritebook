"""Filesystem implementation of publisher skill discovery."""

from pathlib import Path

from ritebook.adapters.outbound.filesystem import (
    DiscoveredSkillFile,
    discover_skill_files,
    read_skill_file_text,
)
from ritebook.features.publisher.domain import SkillEntry


class FilesystemSkillDiscovery:
    """Discover skill entries from directories containing ``SKILL.md`` files."""

    def discover_skills(self, skills_root: str) -> tuple[SkillEntry, ...]:
        """Discover non-hidden skill directories below the explicit skills root."""
        entries = [
            _skill_entry(discovered) for discovered in discover_skill_files(skills_root)
        ]
        return tuple(sorted(entries, key=lambda entry: entry.path))


def _skill_entry(discovered: DiscoveredSkillFile) -> SkillEntry:
    skill_dir = discovered.path.parent
    return SkillEntry(
        name=skill_dir.name,
        path=discovered.relative_skill_dir,
        skill_file=discovered.relative_skill_file,
        title=_extract_title(discovered.path),
    )


def _extract_title(skill_file: Path) -> str | None:
    lines = read_skill_file_text(skill_file).splitlines()
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return title
    return None
