"""Shared filesystem mechanics for discovering skill files."""

from dataclasses import dataclass
from pathlib import Path

from ritebook.adapters.outbound.filesystem import _discovery_helpers
from ritebook.adapters.outbound.filesystem.exceptions import (
    SkillFileReadError,
)

SKILL_FILE_NAME = "SKILL.md"


@dataclass(frozen=True)
class DiscoveredSkillFile:
    """Filesystem facts for a discovered ``SKILL.md`` file."""

    path: Path
    relative_skill_dir: str
    relative_skill_file: str

    @property
    def expected_name(self) -> str:
        """Return the skill name implied by the containing directory."""
        return self.path.parent.name


def discover_skill_files(skills_root: str) -> tuple[DiscoveredSkillFile, ...]:
    """Discover non-hidden ``SKILL.md`` files below an explicit skills root."""
    root = Path(skills_root)
    _discovery_helpers.validate_root(root, skills_root=skills_root)
    return tuple(
        DiscoveredSkillFile(
            path=skill_file,
            relative_skill_dir=_discovery_helpers.relative_skill_dir(
                root=root,
                skill_file=skill_file,
            ),
            relative_skill_file=_discovery_helpers.relative_skill_file(
                root=root,
                skill_file=skill_file,
                skill_file_name=SKILL_FILE_NAME,
            ),
        )
        for skill_file in _discovery_helpers.skill_files(
            root,
            skill_file_name=SKILL_FILE_NAME,
        )
    )


def read_skill_file_text(skill_file: Path) -> str:
    """Read a discovered skill file as UTF-8 text."""
    try:
        return skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as err:
        msg = f"Unable to read discovered skill file: {skill_file}"
        raise SkillFileReadError(msg) from err
