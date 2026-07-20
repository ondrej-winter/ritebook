"""Build source-repository-relative installation provenance paths."""

from pathlib import PurePosixPath

from ritebook.features.skill_installation.application.errors import (
    UnsafeInstallPathError,
)


def repository_relative_source_path(source_root: str, path: str) -> str:
    """Join a catalog-relative path to its repository-relative source root."""
    root = _safe_relative_posix_path(source_root, field_name="skill source root")
    relative_path = _safe_relative_posix_path(path, field_name="skill path")
    return str(root / relative_path)


def _safe_relative_posix_path(value: str, *, field_name: str) -> PurePosixPath:
    if "\\" in value:
        msg = f"{field_name} must use POSIX-style relative paths"
        raise UnsafeInstallPathError(msg)
    path = PurePosixPath(value)
    if path.is_absolute() or not value or any(part == ".." for part in path.parts):
        msg = f"{field_name} must be a safe relative path"
        raise UnsafeInstallPathError(msg)
    return path
