"""Regenerate contribution indexes through the publisher application boundary."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)
from ritebook.features.publisher.application.errors import PublisherError
from ritebook.features.skill_contribution.application.errors import (
    ContributionIndexRegenerationError,
    SkillContributionValidationError,
)
from ritebook.features.skill_contribution.application.ports import IndexRegeneratorPort

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ritebook.features.publisher.application.ports import PublishIndexPort
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionWorkspace,
    )


class PublisherIndexRegeneratorAdapter(IndexRegeneratorPort):
    """Regenerate contribution indexes by delegating to the publisher use case."""

    def __init__(self, *, publisher: PublishIndexPort) -> None:
        """Initialize the adapter with the published index-generation boundary."""
        self._publisher = publisher

    def regenerate_index(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        """Publish ritebook-index.json in the isolated contribution checkout."""
        checkout_path = Path(workspace.checkout_path)
        _validate_index_path(checkout_path)
        skills_root = _published_skills_root(checkout_path, entry.skill_path)
        command = PublishIndexCommand(
            index_name=entry.index_name,
            skills_root=str(checkout_path / skills_root),
            published_skills_root=skills_root,
        )
        try:
            with _working_directory(checkout_path):
                self._publisher.execute(command)
        except PublishIndexValidationError as err:
            message = (
                "skill validation failed during index regeneration; "
                "contribution commit was not created"
            )
            raise SkillContributionValidationError(message) from err
        except PublisherError as err:
            message = (
                "index regeneration could not be completed; "
                "contribution commit was not created"
            )
            raise ContributionIndexRegenerationError(message) from err
        except OSError as err:
            message = (
                "index regeneration could not be completed; "
                "contribution commit was not created"
            )
            raise ContributionIndexRegenerationError(message) from err


def _validate_index_path(checkout_path: Path) -> None:
    index_path = checkout_path / "ritebook-index.json"
    try:
        _reject_symlink_components(checkout_path)
        if (
            not checkout_path.is_dir()
            or checkout_path.is_symlink()
            or not index_path.is_file()
            or index_path.is_symlink()
        ):
            raise _index_read_error()
        resolved_checkout = checkout_path.resolve(strict=True)
        resolved_index = index_path.resolve(strict=True)
    except ContributionIndexRegenerationError:
        raise
    except OSError as err:
        raise _index_read_error() from err
    if not resolved_index.is_relative_to(resolved_checkout):
        raise _index_read_error()


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts:
        if part == path.anchor:
            continue
        current /= part
        if current.is_symlink():
            raise _index_read_error()


def _published_skills_root(checkout_path: Path, skill_path: str) -> str:
    index_path = checkout_path / "ritebook-index.json"
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise _index_read_error() from err
    if not isinstance(payload, dict):
        raise _index_read_error()

    skills_root = payload.get("skills_root", ".")
    if not isinstance(skills_root, str) or not skills_root:
        raise _index_read_error()
    root_path = PurePosixPath(skills_root)
    if (
        root_path.is_absolute()
        or "\\" in skills_root
        or any(part == ".." for part in root_path.parts)
    ):
        raise _index_read_error()
    try:
        PurePosixPath(skill_path).relative_to(root_path)
    except ValueError as err:
        raise _index_read_error() from err
    return skills_root


def _index_read_error() -> ContributionIndexRegenerationError:
    message = (
        "existing index metadata could not be read safely; "
        "contribution commit was not created"
    )
    return ContributionIndexRegenerationError(message)


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    """Run a synchronous adapter operation from a selected directory."""
    previous_directory = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous_directory)
