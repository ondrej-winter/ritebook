"""Application errors for skill installation workflows."""


class SkillInstallationError(Exception):
    """Base class for user-facing skill installation errors."""


class InvalidSkillReferenceError(SkillInstallationError):
    """Raised when a skill reference cannot be parsed."""


class UnknownInstallIndexError(SkillInstallationError):
    """Raised when an installation references an unknown index."""

    def __init__(self, name: str) -> None:
        """Build an unknown-index error for CLI rendering."""
        super().__init__(f"unknown index: {name}")


class UnknownInstallSkillError(SkillInstallationError):
    """Raised when an installation references an unknown skill."""

    def __init__(self, requirement: str) -> None:
        """Build an unknown-skill error for CLI rendering."""
        super().__init__(f"unknown skill {requirement}")


class UndefinedInstallTargetError(SkillInstallationError):
    """Raised when a requirement references an undefined target nickname."""

    def __init__(self, nickname: str, requirements_file: str) -> None:
        """Build an undefined-target error for CLI rendering."""
        super().__init__(
            f"target nickname {nickname} is not defined in {requirements_file}",
        )


class DuplicateSkillRequirementError(SkillInstallationError):
    """Raised when a requirements file repeats a skill requirement."""

    def __init__(self, requirement: str) -> None:
        """Build a duplicate-requirement error for CLI rendering."""
        super().__init__(f"duplicate skill requirement: {requirement}")


class DuplicateInstallTargetError(SkillInstallationError):
    """Raised when multiple requirements resolve to the same target."""

    def __init__(self, target: str) -> None:
        """Build a duplicate-target error for CLI rendering."""
        super().__init__(f"duplicate install target: {target}")


class ExistingInstallTargetError(SkillInstallationError):
    """Raised when an install target exists and force was not requested."""

    def __init__(self, target: str) -> None:
        """Build an existing-target error for CLI rendering."""
        super().__init__(f"target {target} already exists; use --force to replace it")


class ConflictingRecordedTargetError(SkillInstallationError):
    """Raised when recorded installation state conflicts with a target."""


class UnsafeInstallPathError(SkillInstallationError):
    """Raised when an install source or target path is unsafe."""


class InstallationPersistenceError(SkillInstallationError):
    """Raised when generated installation state cannot be persisted."""


class SkillSourceResolutionError(SkillInstallationError):
    """Raised when source repository metadata cannot be resolved."""


class PartialInstallationError(SkillInstallationError):
    """Raised when requirements installation copied some skills before failing."""

    def __init__(self) -> None:
        """Build a partial-install failure error for CLI rendering."""
        super().__init__(
            "installation failed after copying one or more skills; "
            "ritebook.lock was not updated and copied directories may remain",
        )
