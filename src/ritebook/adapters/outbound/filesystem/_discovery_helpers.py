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


def named_file_candidates(
    root: Path,
    *,
    file_name: str,
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Return regular named files and visible symlinked candidate paths."""
    discovered: list[Path] = []
    symlinks: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        named_file, symlink = _named_file_candidate(directory, file_name=file_name)
        if named_file is not None:
            discovered.append(named_file)
        if symlink is not None:
            symlinks.append(symlink)
        children = _directory_children(directory)
        child_directories, child_symlinks = _visible_child_candidates(
            children,
            file_name=file_name,
        )
        pending.extend(reversed(child_directories))
        symlinks.extend(child_symlinks)
    return tuple(sorted(discovered)), tuple(sorted(symlinks))


def _named_file_candidate(
    directory: Path,
    *,
    file_name: str,
) -> tuple[Path | None, Path | None]:
    named_file = directory / file_name
    try:
        if named_file.is_symlink():
            return None, named_file
        if named_file.is_file():
            return named_file, None
    except OSError as err:
        msg = f"Unable to inspect skill candidate: {named_file}"
        raise FilesystemSkillDiscoveryError(msg) from err
    return None, None


def _directory_children(directory: Path) -> tuple[Path, ...]:
    try:
        return tuple(sorted(directory.iterdir(), key=lambda path: path.name))
    except OSError as err:
        msg = f"Unable to read directory while discovering skills: {directory}"
        raise FilesystemSkillDiscoveryError(msg) from err


def _visible_child_candidates(
    children: tuple[Path, ...],
    *,
    file_name: str,
) -> tuple[list[Path], list[Path]]:
    directories: list[Path] = []
    symlinks: list[Path] = []
    for child in children:
        if child.name.startswith("."):
            continue
        try:
            if child.is_symlink():
                linked_named_file = child / file_name
                if linked_named_file.is_file() or linked_named_file.is_symlink():
                    symlinks.append(linked_named_file)
            elif child.is_dir():
                directories.append(child)
        except OSError as err:
            msg = f"Unable to inspect path while discovering skills: {child}"
            raise FilesystemSkillDiscoveryError(msg) from err
    return directories, symlinks


def relative_file_dir(*, root: Path, discovered_file: Path) -> str:
    """Format the discovered file directory relative to ``root``."""
    relative_dir = discovered_file.parent.relative_to(root)
    return "." if relative_dir == Path() else relative_dir.as_posix()


def relative_file_path(*, root: Path, discovered_file: Path, file_name: str) -> str:
    """Format the discovered file path relative to ``root``."""
    path = relative_file_dir(root=root, discovered_file=discovered_file)
    return file_name if path == "." else f"{path}/{file_name}"
