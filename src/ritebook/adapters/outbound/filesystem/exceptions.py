"""Shared filesystem adapter exceptions for skill discovery."""


class FilesystemSkillDiscoveryError(Exception):
    """Base error raised when filesystem skill discovery fails."""


class SkillsRootNotFoundError(FilesystemSkillDiscoveryError):
    """Raised when the configured skills root does not exist."""


class SkillsRootNotDirectoryError(FilesystemSkillDiscoveryError):
    """Raised when the configured skills root is not a directory."""


class SkillFileReadError(FilesystemSkillDiscoveryError):
    """Raised when a discovered skill file cannot be read safely."""
