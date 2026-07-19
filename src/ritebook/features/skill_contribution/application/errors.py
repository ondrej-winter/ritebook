"""Application errors for skill contribution workflows."""


class SkillContributionError(Exception):
    """Base class for user-facing skill contribution errors."""


class InvalidContributionSkillReferenceError(SkillContributionError):
    """Raised when a contribution skill reference cannot be parsed."""


class ContributionLockfileReadError(SkillContributionError):
    """Raised when a contribution lockfile cannot be read or parsed."""


class ContributionLockfileEntryNotFoundError(SkillContributionError):
    """Raised when no publishable lockfile entry matches a reference."""


class AmbiguousContributionSkillReferenceError(SkillContributionError):
    """Raised when a contribution selector matches multiple lockfile entries."""


class IncompleteContributionProvenanceError(SkillContributionError):
    """Raised when a lockfile entry lacks required contribution provenance."""


class MissingInstalledSkillTargetError(SkillContributionError):
    """Raised when the installed skill target is missing or unusable."""


class UpstreamSkillChangedError(SkillContributionError):
    """Raised when upstream changed since the locked installation revision."""

    def __init__(self) -> None:
        """Build an upstream-change error with remediation guidance."""
        super().__init__(
            "upstream changed since locked revision; update or reinstall the skill "
            "or reconcile the source changes manually before retrying",
        )


class SkillContributionValidationError(SkillContributionError):
    """Raised when changed skill validation fails before commit creation."""


class ContributionIndexRegenerationError(SkillContributionError):
    """Raised when contribution index regeneration fails before commit creation."""


class ContributionGitError(SkillContributionError):
    """Raised when isolated contribution Git operations fail."""


class UnsafeContributionPathError(SkillContributionError):
    """Raised when a contribution path escapes an approved boundary."""
