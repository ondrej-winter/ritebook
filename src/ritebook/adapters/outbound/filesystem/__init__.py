"""Shared filesystem adapter utilities."""

from ritebook.adapters.outbound.filesystem.discovery import (
    SKILL_FILE_NAME,
    DiscoveredSkillFile,
    discover_skill_files,
    read_skill_file_text,
)
from ritebook.adapters.outbound.filesystem.exceptions import (
    FilesystemSkillDiscoveryError,
    SkillFileReadError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)

__all__ = [
    "SKILL_FILE_NAME",
    "DiscoveredSkillFile",
    "FilesystemSkillDiscoveryError",
    "SkillFileReadError",
    "SkillsRootNotDirectoryError",
    "SkillsRootNotFoundError",
    "discover_skill_files",
    "read_skill_file_text",
]
