"""Application errors for skill installation workflows."""


class SkillInstallationError(Exception):
    """Base class for user-facing skill installation errors."""


class InvalidSkillReferenceError(SkillInstallationError):
    """Raised when a skill reference cannot be parsed."""


class UnknownInstallIndexError(SkillInstallationError):
    """Raised when an installation references an unknown local alias."""

    def __init__(self, name: str) -> None:
        """Build an unknown-local-alias error for CLI rendering."""
        super().__init__(f"unknown local alias: {name}")


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
    """Raised when requirements resolve to overlapping filesystem targets."""

    def __init__(self, target: str) -> None:
        """Build a duplicate-target error for CLI rendering."""
        super().__init__(f"duplicate install target: {target}")


class ExistingInstallTargetError(SkillInstallationError):
    """Raised when an install target exists and force was not requested."""

    def __init__(self, target: str) -> None:
        """Build an existing-target error for CLI rendering."""
        super().__init__(f"target {target} already exists; use --force to replace it")


class UnmanagedInstallTargetError(SkillInstallationError):
    """Raised when an existing target is not owned by Ritebook."""

    def __init__(self, target: str) -> None:
        """Build an unmanaged-target error for CLI rendering."""
        super().__init__(f"target {target} exists but is not owned by Ritebook")


class LocallyModifiedInstallTargetError(SkillInstallationError):
    """Raised when an owned target differs from its last committed digest."""

    def __init__(self, target: str) -> None:
        """Build a local-edit preservation error for CLI rendering."""
        super().__init__(f"target {target} has local changes and was preserved")


class IndexRefreshError(SkillInstallationError):
    """Raised when a referenced registered index cannot be refreshed safely."""


class UnsafeInstallPathError(SkillInstallationError):
    """Raised when an install source or target path is unsafe."""


class InstallationPersistenceError(SkillInstallationError):
    """Raised when generated installation state cannot be persisted."""


class InstallationBusyError(InstallationPersistenceError):
    """Raised when another installation process owns the operation lock."""


class RequirementsReadError(SkillInstallationError):
    """Raised when an installation requirements file cannot be read or parsed."""


class SkillSourceResolutionError(SkillInstallationError):
    """Raised when source repository metadata cannot be resolved."""


class CommittedSkillValidationError(SkillInstallationError):
    """Raised when a selected committed skill header cannot be validated."""


class CommittedSkillMetadataMismatchError(SkillInstallationError):
    """Raised when committed skill metadata differs from the bound index."""

    def __init__(self, skill_path: str) -> None:
        """Build a mismatch error without exposing source contents."""
        super().__init__(
            f"committed skill header does not match indexed metadata: {skill_path}",
        )
