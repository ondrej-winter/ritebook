"""Application errors for publisher workflows."""


class PublisherError(Exception):
    """Base application error for publisher workflows."""


class PublishIndexDiscoveryError(PublisherError):
    """Raised when skills cannot be discovered for index publication."""


class PublishIndexWriteError(PublisherError):
    """Raised when a publisher index cannot be written."""
