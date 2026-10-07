import pytest

from ritebook.features.index_registry.application.dtos import (
    UpdateIndexCommand,
    UpdateIndexResult,
)
from ritebook.features.index_registry.application.errors import IndexSourceError
from ritebook.features.skill_installation.adapters.outbound import (
    IndexRegistryRefresherAdapter,
)
from ritebook.features.skill_installation.application.errors import IndexRefreshError


class _UpdateIndex:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.commands: list[UpdateIndexCommand] = []

    def execute(self, command: UpdateIndexCommand) -> UpdateIndexResult:
        self.commands.append(command)
        if self.failure is not None:
            raise self.failure
        return UpdateIndexResult(name=command.name, skill_count=2)


def test_index_refresher_updates_exact_referenced_alias() -> None:
    update_index = _UpdateIndex()

    IndexRegistryRefresherAdapter(update_index=update_index).refresh(
        "platform-skills",
        "/tmp/indexes.json",
    )

    assert len(update_index.commands) == 1
    command = update_index.commands[0]
    assert command.name == "platform-skills"
    assert command.all is False
    assert command.registry_path == "/tmp/indexes.json"


def test_index_refresher_translates_registry_failure_without_stale_fallback() -> None:
    adapter = IndexRegistryRefresherAdapter(
        update_index=_UpdateIndex(IndexSourceError("refresh failed")),
    )

    with pytest.raises(IndexRefreshError, match=r"platform-skills.*refresh failed"):
        adapter.refresh("platform-skills", None)
