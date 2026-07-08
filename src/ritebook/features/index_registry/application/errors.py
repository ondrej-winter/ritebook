"""Application errors for consumer index registration."""


class IndexRegistryError(Exception):
    """Base class for user-facing index registry errors."""


class DuplicateIndexNameError(IndexRegistryError):
    """Raised when adding an index would replace an existing name."""

    def __init__(self, name: str) -> None:
        """Build a duplicate-name error for CLI rendering."""
        super().__init__(f"index {name} already exists; use --force to replace it")


class UnknownIndexNameError(IndexRegistryError):
    """Raised when updating an unregistered index name."""

    def __init__(self, name: str) -> None:
        """Build an unknown-name error for CLI rendering."""
        super().__init__(f"index {name} is not registered")


class InvalidPublishedIndexError(IndexRegistryError):
    """Raised when a published index cannot be accepted by the registry."""


class IndexRegistryPersistenceError(IndexRegistryError):
    """Raised when registry metadata cannot be loaded or saved."""


class IndexCacheError(IndexRegistryError):
    """Raised when cached index contents cannot be written."""


class IndexSourceError(IndexRegistryError):
    """Raised when a Git source cannot be prepared or refreshed."""
