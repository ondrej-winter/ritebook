"""Regenerate contribution indexes through the publisher application boundary."""

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
)
from ritebook.features.publisher.application.errors import PublisherError
from ritebook.features.publisher.application.ports import PublishIndexPort
from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
)
from ritebook.features.skill_contribution.application.errors import (
    ContributionIndexRegenerationError,
    SkillContributionValidationError,
)
from ritebook.features.skill_contribution.application.ports import IndexRegeneratorPort


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
