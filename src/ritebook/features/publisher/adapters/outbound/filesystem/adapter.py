"""Filesystem implementation of publisher skill discovery."""

from pathlib import Path

from ritebook.features.linter.adapters.outbound.filesystem.exceptions import (
    FilesystemSkillDiscoveryError,
    SkillFileReadError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)
from ritebook.features.publisher.domain import SkillEntry

SKILL_FILE_NAME = "SKILL.md"


class FilesystemSkillDiscovery:
    """Discover skill entries from directories containing ``SKILL.md`` files."""

    def discover_skills(self, skills_root: str) -> tuple[SkillEntry, ...]:
        """Discover non-hidden skill directories below the explicit skills root."""
        root = Path(skills_root)
        _validate_root(root, skills_root=skills_root)

        entries = [
            _skill_entry(root=root, skill_file=path) for path in _skill_files(root)
        ]
        return tuple(sorted(entries, key=lambda entry: entry.path))


def _validate_root(root: Path, *, skills_root: str) -> None:
    try:
        if not root.exists():
            msg = f"Skills root does not exist: {skills_root}"
            raise SkillsRootNotFoundError(msg)
        if not root.is_dir():
            msg = f"Skills root is not a directory: {skills_root}"
            raise SkillsRootNotDirectoryError(msg)
    except OSError as err:
        msg = f"Unable to inspect skills root: {skills_root}"
        raise FilesystemSkillDiscoveryError(msg) from err


def _skill_files(root: Path) -> tuple[Path, ...]:
    discovered: list[Path] = []
    _collect_skill_files(root, discovered=discovered)
    return tuple(discovered)


def _collect_skill_files(directory: Path, *, discovered: list[Path]) -> None:
    skill_file = directory / SKILL_FILE_NAME
    if skill_file.is_file():
        discovered.append(skill_file)

    try:
        children = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError as err:
        msg = f"Unable to read directory while discovering skills: {directory}"
        raise FilesystemSkillDiscoveryError(msg) from err

    for child in children:
        if child.name.startswith(".") or not child.is_dir():
            continue
        _collect_skill_files(child, discovered=discovered)


def _skill_entry(*, root: Path, skill_file: Path) -> SkillEntry:
    skill_dir = skill_file.parent
    path = _relative_skill_dir(root=root, skill_file=skill_file)
    skill_file_path = _relative_skill_file(root=root, skill_file=skill_file)
    return SkillEntry(
        name=skill_dir.name,
        path=path,
        skill_file=skill_file_path,
        title=_extract_title(skill_file),
    )


def _relative_skill_dir(*, root: Path, skill_file: Path) -> str:
    relative_dir = skill_file.parent.relative_to(root)
    return "." if relative_dir == Path() else relative_dir.as_posix()


def _relative_skill_file(*, root: Path, skill_file: Path) -> str:
    path = _relative_skill_dir(root=root, skill_file=skill_file)
    return SKILL_FILE_NAME if path == "." else f"{path}/{SKILL_FILE_NAME}"


def _extract_title(skill_file: Path) -> str | None:
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as err:
        msg = f"Unable to read discovered skill file: {skill_file}"
        raise SkillFileReadError(msg) from err

    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return title
    return None
