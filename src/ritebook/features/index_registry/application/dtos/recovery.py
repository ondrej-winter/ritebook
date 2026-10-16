"""Source registrations retained for explicit legacy-registry rebuilding."""

from dataclasses import dataclass

from ritebook.features.index_registry.application.dtos.index_registry import IndexSourceType
from ritebook.shared_kernel import require_index_name, require_safe_persisted_source


@dataclass(frozen=True)
class RecoverableIndex:
    """A validated source locator without trusted cache or provenance metadata."""

    name: str
    source: str
    source_type: IndexSourceType

    def __post_init__(self) -> None:
        """Validate the only legacy fields recovery may consume."""
        require_index_name(self.name, field_name="Local alias")
        if not self.source.strip():
            msg = "Index source must not be empty."
            raise ValueError(msg)
        require_safe_persisted_source(self.source, self.source_type.value)
