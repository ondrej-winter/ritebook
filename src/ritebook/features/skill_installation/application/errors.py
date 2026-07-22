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


class ConflictingRecordedTargetError(SkillInstallationError):
    """Raised when recorded installation state conflicts with a target."""


class UnsafeInstallPathError(SkillInstallationError):
    """Raised when an install source or target path is unsafe."""


class InstallationPersistenceError(SkillInstallationError):
    """Raised when generated installation state cannot be persisted."""


class InstalledTargetCleanupError(InstallationPersistenceError):
    """Raised when a target is installed but its prior backup remains."""

    def __init__(self, *, target: str, backup_path: str) -> None:
        """Build recovery guidance for an installed target and retained backup."""
        self.target = target
        self.backup_path = backup_path
        super().__init__(
            f"target {target} was installed but prior backup cleanup failed; "
            f"remove backup {backup_path} after verifying the installed target",
        )


class GeneratedStateCommitError(SkillInstallationError):
    """Raised when copied targets remain after generated-state commit failure."""

    def __init__(
        self,
        artifact: str,
        copied_targets: tuple[str, ...],
        recovery_detail: str | None = None,
    ) -> None:
        """Build recovery guidance for retained copied targets."""
        targets = ", ".join(copied_targets)
        recovery = f"; {recovery_detail}" if recovery_detail is not None else ""
        super().__init__(
            f"installation copied target(s) {targets}, but {artifact} was not updated; "
            "copied directories remain, so inspect them and retry the installation"
            f"{recovery}",
        )


class RequirementsReadError(SkillInstallationError):
    """Raised when an installation requirements file cannot be read or parsed."""


class SkillSourceResolutionError(SkillInstallationError):
    """Raised when source repository metadata cannot be resolved."""


class PartialInstallationError(SkillInstallationError):
    """Raised when requirements installation copied some skills before failing."""

    def __init__(
        self,
        copied_targets: tuple[str, ...] = (),
        recovery_detail: str | None = None,
    ) -> None:
        """Build a partial-install failure error for CLI rendering."""
        target_summary = f" ({', '.join(copied_targets)})" if copied_targets else ""
        recovery = f"; {recovery_detail}" if recovery_detail is not None else ""
        super().__init__(
            f"installation failed after copying one or more skills{target_summary}; "
            "ritebook.lock was not updated and copied directories may remain"
            f"{recovery}",
        )
