"""Internal filesystem discovery helpers."""

from pathlib import Path

from ritebook.adapters.outbound.filesystem.exceptions import (
    FilesystemSkillDiscoveryError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)


def validate_root(root: Path) -> None:
    """Validate that the configured skills root exists and is a directory."""
    try:
        if not root.exists():
            msg = f"Skills root does not exist: {root}"
            raise SkillsRootNotFoundError(msg)
        if not root.is_dir():
            msg = f"Skills root is not a directory: {root}"
            raise SkillsRootNotDirectoryError(msg)
    except OSError as err:
        msg = f"Unable to inspect skills root: {root}"
        raise FilesystemSkillDiscoveryError(msg) from err


def named_files(root: Path, *, file_name: str) -> tuple[Path, ...]:
    """Return non-hidden named files discovered recursively below ``root``."""
    return collect_named_files(root, file_name=file_name)


def collect_named_files(
    directory: Path,
    *,
    file_name: str,
) -> tuple[Path, ...]:
    """Return matching named files from ``directory`` and visible descendants."""
    discovered: list[Path] = []
    named_file = directory / file_name
    if named_file.is_file():
        discovered.append(named_file)

    try:
        children = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError as err:
        msg = f"Unable to read directory while discovering skills: {directory}"
        raise FilesystemSkillDiscoveryError(msg) from err

    for child in children:
        if child.name.startswith(".") or child.is_symlink() or not child.is_dir():
            continue
        discovered.extend(
            collect_named_files(
                child,
                file_name=file_name,
            ),
        )
    return tuple(discovered)


def relative_file_dir(*, root: Path, discovered_file: Path) -> str:
    """Format the discovered file directory relative to ``root``."""
    relative_dir = discovered_file.parent.relative_to(root)
    return "." if relative_dir == Path() else relative_dir.as_posix()


def relative_file_path(*, root: Path, discovered_file: Path, file_name: str) -> str:
    """Format the discovered file path relative to ``root``."""
    path = relative_file_dir(root=root, discovered_file=discovered_file)
    return file_name if path == "." else f"{path}/{file_name}"
