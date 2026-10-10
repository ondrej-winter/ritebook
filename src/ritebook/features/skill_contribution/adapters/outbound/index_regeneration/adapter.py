"""Regenerate contribution indexes through the publisher application boundary."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)
from ritebook.features.publisher.application.errors import PublisherError
from ritebook.features.skill_contribution.application.dtos import (
    ContributionSkillReference,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionIndexRegenerationError,
    SkillContributionValidationError,
)
from ritebook.features.skill_contribution.application.ports import IndexRegeneratorPort
from ritebook.shared_kernel import SchemaV1CatalogError, parse_schema_v1_catalog_bytes

if TYPE_CHECKING:
    from collections.abc import Generator

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
        _validate_checkout_path(checkout_path)
        published_name = _published_name(checkout_path)
        skills_root = _published_skills_root(entry)
        command = PublishIndexCommand(
            index_name=published_name,
            skills_root=str(checkout_path / skills_root),
            published_skills_root=skills_root,
        )
        try:
            with _working_directory(checkout_path):
                self._publisher.execute(command)
        except PublishIndexValidationError as err:
            message = "skill validation failed during index regeneration; contribution commit was not created"
            raise SkillContributionValidationError(message) from err
        except PublisherError as err:
            message = "index regeneration could not be completed; contribution commit was not created"
            raise ContributionIndexRegenerationError(message) from err
        except OSError as err:
            message = "index regeneration could not be completed; contribution commit was not created"
            raise ContributionIndexRegenerationError(message) from err


def _validate_checkout_path(checkout_path: Path) -> None:
    try:
        _reject_symlink_components(checkout_path)
        if not checkout_path.is_dir() or checkout_path.is_symlink():
            raise _checkout_error()
        checkout_path.resolve(strict=True)
    except ContributionIndexRegenerationError:
        raise
    except OSError as err:
        raise _checkout_error() from err


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts:
        if part == path.anchor:
            continue
        current /= part
        if current.is_symlink():
            raise _checkout_error()


def _published_name(checkout_path: Path) -> str:
    index_path = checkout_path / "ritebook-index.json"
    try:
        if not index_path.is_file() or index_path.is_symlink():
            raise _index_read_error()
        resolved_checkout = checkout_path.resolve(strict=True)
        resolved_index = index_path.resolve(strict=True)
        if not resolved_index.is_relative_to(resolved_checkout):
            raise _index_read_error()
        catalog = parse_schema_v1_catalog_bytes(index_path.read_bytes())
    except ContributionIndexRegenerationError:
        raise
    except (OSError, SchemaV1CatalogError) as err:
        raise _index_read_error() from err
    return catalog.published_name


def _published_skills_root(entry: ContributionLockfileEntry) -> str:
    try:
        selector = PurePosixPath(
            ContributionSkillReference.parse(entry.requirement).skill_selector,
        )
        skill_path = PurePosixPath(entry.skill_path)
    except ValueError as err:
        raise _provenance_error() from err
    selector_depth = len(selector.parts)
    if skill_path.parts[-selector_depth:] != selector.parts:
        raise _provenance_error()
    root_parts = skill_path.parts[:-selector_depth]
    return PurePosixPath(*root_parts).as_posix() if root_parts else "."


def _checkout_error() -> ContributionIndexRegenerationError:
    message = "contribution checkout could not be used safely; contribution commit was not created"
    return ContributionIndexRegenerationError(message)


def _index_read_error() -> ContributionIndexRegenerationError:
    message = "existing index metadata could not be read safely; contribution commit was not created"
    return ContributionIndexRegenerationError(message)


def _provenance_error() -> ContributionIndexRegenerationError:
    message = "contribution provenance does not identify a catalog root; contribution commit was not created"
    return ContributionIndexRegenerationError(message)


@contextmanager
def _working_directory(path: Path) -> Generator[None]:
    """Run a synchronous adapter operation from a selected directory."""
    previous_directory = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous_directory)
