"""Regenerate contribution indexes through the publisher application boundary."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
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
        command = PublishIndexCommand(
            index_name=entry.index_name,
            skills_root=workspace.checkout_path,
        )
        try:
            with _working_directory(Path(workspace.checkout_path)):
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


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    """Run a synchronous adapter operation from a selected directory."""
    previous_directory = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous_directory)
