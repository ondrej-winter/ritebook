"""Shared filesystem mechanics for discovering named files."""

from dataclasses import dataclass
from pathlib import Path

from ritebook.adapters.outbound.filesystem import _discovery_helpers
from ritebook.adapters.outbound.filesystem.exceptions import SkillFileReadError


@dataclass(frozen=True)
class DiscoveredNamedFile:
    """Filesystem facts for a discovered named file."""

    path: Path
    relative_dir: str
    relative_file: str

    @property
    def directory_name(self) -> str:
        """Return the name implied by the containing directory."""
        return self.path.parent.name


def discover_named_files(
    root: Path,
    *,
    file_name: str,
) -> tuple[DiscoveredNamedFile, ...]:
    """Discover non-hidden files with ``file_name`` below an explicit root."""
    _discovery_helpers.validate_root(root)
    return tuple(
        DiscoveredNamedFile(
            path=discovered_file,
            relative_dir=_discovery_helpers.relative_file_dir(
                root=root,
                discovered_file=discovered_file,
            ),
            relative_file=_discovery_helpers.relative_file_path(
                root=root,
                discovered_file=discovered_file,
                file_name=file_name,
            ),
        )
        for discovered_file in _discovery_helpers.named_files(
            root,
            file_name=file_name,
        )
    )


def read_skill_file_text(skill_file: Path) -> str:
    """Read a discovered skill file as UTF-8 text."""
    try:
        return skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as err:
        msg = f"Unable to read discovered skill file: {skill_file}"
        raise SkillFileReadError(msg) from err
