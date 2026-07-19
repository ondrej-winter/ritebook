"""Safely compare and copy skill directories for contributions."""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path, PurePosixPath

from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
    SkillChangeComparison,
    SkillChangeStatus,
)
from ritebook.features.skill_contribution.application.errors import (
    MissingInstalledSkillTargetError,
    SkillContributionError,
    UnsafeContributionPathError,
)
from ritebook.features.skill_contribution.application.ports import (
    SkillChangeDetectorPort,
    SkillDirectoryPort,
)

SKILL_FILE_NAME = "SKILL.md"


class FilesystemSkillDirectoryAdapter(SkillChangeDetectorPort, SkillDirectoryPort):
    """Compare installed skills and copy them into contribution checkouts."""

    def compare(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> SkillChangeComparison:
        """Compare installed and current upstream skill directories."""
        installed_path = _installed_skill_path(entry)
        source_path = _source_skill_path(entry, workspace)
        _validate_skill_directory(installed_path, description="installed skill target")
        _validate_skill_directory(source_path, description="source skill directory")
        changed_file_count = _changed_file_count(installed_path, source_path)
        status = (
            SkillChangeStatus.NO_CHANGES
            if changed_file_count == 0
            else SkillChangeStatus.CHANGED
        )
        return SkillChangeComparison(
            status=status,
            installed_path=str(installed_path),
            source_skill_path=entry.skill_path,
            changed_file_count=changed_file_count,
        )

    def copy_installed_skill(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        """Replace the selected checkout skill directory with installed content."""
        installed_path = _installed_skill_path(entry)
        source_path = _source_skill_path(entry, workspace)
        _validate_skill_directory(installed_path, description="installed skill target")
        _validate_destination_parent(source_path.parent, _checkout_path(workspace))

        if source_path.exists() or source_path.is_symlink():
            _validate_skill_directory(source_path, description="source skill directory")
            shutil.rmtree(source_path)
        shutil.copytree(installed_path, source_path, symlinks=False)


def _installed_skill_path(entry: ContributionLockfileEntry) -> Path:
    path = Path(entry.target).expanduser()
    if not path.exists() or not path.is_dir() or path.is_symlink():
        msg = (
            f"installed skill target {entry.target} does not exist "
            "or is not a directory"
        )
        raise MissingInstalledSkillTargetError(msg)
    return path.resolve(strict=True)


def _source_skill_path(
    entry: ContributionLockfileEntry,
    workspace: ContributionWorkspace,
) -> Path:
    _validate_source_paths(entry, workspace)
    checkout_path = _checkout_path(workspace)
    candidate = checkout_path.joinpath(*PurePosixPath(entry.skill_path).parts)
    _require_inside_checkout(candidate, checkout_path)
    return candidate


def _checkout_path(workspace: ContributionWorkspace) -> Path:
    path = Path(workspace.checkout_path).expanduser()
    if not path.exists() or not path.is_dir() or path.is_symlink():
        msg = "contribution checkout does not exist or is not a directory"
        raise UnsafeContributionPathError(msg)
    return path.resolve(strict=True)


def _validate_source_paths(
    entry: ContributionLockfileEntry,
    workspace: ContributionWorkspace,
) -> None:
    skill_path = _safe_relative_path(entry.skill_path, field_name="skill_path")
    skill_file = _safe_relative_path(entry.skill_file, field_name="skill_file")
    workspace_skill_path = _safe_relative_path(
        workspace.source_skill_path,
        field_name="workspace source skill path",
    )
    if skill_path != workspace_skill_path:
        msg = "workspace source skill path does not match lockfile skill_path"
        raise UnsafeContributionPathError(msg)
    if not _is_relative_to(skill_file, skill_path):
        msg = "skill_file must be inside skill_path"
        raise UnsafeContributionPathError(msg)
    if skill_file.name != SKILL_FILE_NAME:
        msg = "skill_file must point to SKILL.md"
        raise UnsafeContributionPathError(msg)


def _safe_relative_path(value: str, *, field_name: str) -> PurePosixPath:
    if value.startswith("/") or value.endswith("/") or "//" in value or "\\" in value:
        msg = f"{field_name} must be a safe relative POSIX path"
        raise UnsafeContributionPathError(msg)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
    ):
        msg = f"{field_name} must be a safe relative POSIX path"
        raise UnsafeContributionPathError(msg)
    return path


def _require_inside_checkout(candidate: Path, checkout_path: Path) -> Path:
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as err:
        msg = "source skill path cannot be resolved safely"
        raise UnsafeContributionPathError(msg) from err
    if not resolved.is_relative_to(checkout_path):
        msg = "source skill path escapes the contribution checkout"
        raise UnsafeContributionPathError(msg)
    return resolved


def _validate_destination_parent(parent: Path, checkout_path: Path) -> None:
    current = checkout_path
    for relative_part in parent.relative_to(checkout_path).parts:
        current = current / relative_part
        if current.is_symlink():
            msg = "source skill path contains a symlink"
            raise UnsafeContributionPathError(msg)
    resolved_parent = _require_inside_checkout(parent, checkout_path)
    resolved_parent.mkdir(parents=True, exist_ok=True)


def _validate_skill_directory(path: Path, *, description: str) -> None:
    if not path.exists() or not path.is_dir() or path.is_symlink():
        msg = f"{description} {path} does not exist or is not a directory"
        raise SkillContributionError(msg)
    if not (path / SKILL_FILE_NAME).is_file() or (path / SKILL_FILE_NAME).is_symlink():
        msg = f"{description} {path} is missing SKILL.md"
        raise SkillContributionError(msg)
    _reject_symlinks(path, description=description)


def _reject_symlinks(root: Path, *, description: str) -> None:
    for child in root.rglob("*"):
        if child.is_symlink():
            msg = (
                f"{description} contains unsupported symlink: {child.relative_to(root)}"
            )
            raise UnsafeContributionPathError(msg)


def _changed_file_count(left: Path, right: Path) -> int:
    left_entries = _directory_entries(left)
    right_entries = _directory_entries(right)
    changed_entries = left_entries.symmetric_difference(right_entries)
    common_files = sorted(
        entry
        for entry in left_entries.intersection(right_entries)
        if (left / entry).is_file() and (right / entry).is_file()
    )
    changed_files = sum(
        1
        for entry in common_files
        if not filecmp.cmp(left / entry, right / entry, shallow=False)
    )
    return len(changed_entries) + changed_files


def _directory_entries(root: Path) -> set[Path]:
    return {path.relative_to(root) for path in sorted(root.rglob("*"))}


def _is_relative_to(path: PurePosixPath, parent: PurePosixPath) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
