"""Bridge the index-registry update use case into installation refresh semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import UpdateIndexCommand
from ritebook.features.index_registry.application.errors import IndexRegistryError
from ritebook.features.skill_installation.application.errors import IndexRefreshError

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.ports import UpdateIndexPort


class IndexRegistryRefresherAdapter:
    """Refresh exactly one referenced registered alias without stale fallback."""

    def __init__(self, *, update_index: UpdateIndexPort) -> None:
        """Initialize the bridge with the index-registry inbound application port."""
        self._update_index = update_index

    def refresh(self, name: str, registry_path: str | None) -> None:
        """Refresh one alias or translate failure into an installation error."""
        try:
            self._update_index.execute(
                UpdateIndexCommand(name=name, registry_path=registry_path),
            )
        except (IndexRegistryError, ValueError) as err:
            msg = f"unable to refresh referenced index {name}: {err}"
            raise IndexRefreshError(msg) from err
