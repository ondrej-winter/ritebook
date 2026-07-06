"""Internal filesystem discovery helpers."""

from pathlib import Path

from ritebook.adapters.outbound.filesystem.exceptions import (
    FilesystemSkillDiscoveryError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)


def validate_root(root: Path, *, skills_root: str) -> None:
    """Validate that the configured skills root exists and is a directory."""
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


def skill_files(root: Path, *, skill_file_name: str) -> tuple[Path, ...]:
    """Return non-hidden skill files discovered recursively below ``root``."""
    discovered: list[Path] = []
    collect_skill_files(root, discovered=discovered, skill_file_name=skill_file_name)
    return tuple(discovered)


def collect_skill_files(
    directory: Path,
    *,
    discovered: list[Path],
    skill_file_name: str,
) -> None:
    """Collect matching skill files from ``directory`` and visible descendants."""
    skill_file = directory / skill_file_name
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
        collect_skill_files(
            child,
            discovered=discovered,
            skill_file_name=skill_file_name,
        )


def relative_skill_dir(*, root: Path, skill_file: Path) -> str:
    """Format the discovered skill directory relative to ``root``."""
    relative_dir = skill_file.parent.relative_to(root)
    return "." if relative_dir == Path() else relative_dir.as_posix()


def relative_skill_file(*, root: Path, skill_file: Path, skill_file_name: str) -> str:
    """Format the discovered skill file path relative to ``root``."""
    path = relative_skill_dir(root=root, skill_file=skill_file)
    return skill_file_name if path == "." else f"{path}/{skill_file_name}"
