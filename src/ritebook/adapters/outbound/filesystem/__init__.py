"""Shared filesystem adapter utilities."""

from ritebook.adapters.outbound.filesystem.discovery import (
    DiscoveredNamedFile,
    discover_named_files,
    read_skill_file_text,
)
from ritebook.adapters.outbound.filesystem.exceptions import (
    FilesystemSkillDiscoveryError,
    SkillFileReadError,
    SkillsRootNotDirectoryError,
    SkillsRootNotFoundError,
)
from ritebook.adapters.outbound.filesystem.frontmatter import (
    FrontmatterParseError,
    parse_yaml_frontmatter,
)

__all__ = [
    "DiscoveredNamedFile",
    "FilesystemSkillDiscoveryError",
    "FrontmatterParseError",
    "SkillFileReadError",
    "SkillsRootNotDirectoryError",
    "SkillsRootNotFoundError",
    "discover_named_files",
    "parse_yaml_frontmatter",
    "read_skill_file_text",
]
