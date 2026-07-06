"""Filesystem skill-header discovery adapter."""

from ritebook.features.linter.adapters.outbound.filesystem.adapter import (
    FilesystemSkillHeaderDiscovery,
)
from ritebook.features.linter.adapters.outbound.filesystem.exceptions import (
    FilesystemSkillDiscoveryError,
    SkillFileReadError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)

__all__ = [
    "FilesystemSkillDiscoveryError",
    "FilesystemSkillHeaderDiscovery",
    "SkillFileReadError",
    "SkillsRootNotDirectoryError",
    "SkillsRootNotFoundError",
]
