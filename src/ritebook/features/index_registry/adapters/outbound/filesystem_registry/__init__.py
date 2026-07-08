"""Filesystem index registry metadata adapter."""

from ritebook.features.index_registry.adapters.outbound.filesystem_registry import (
    adapter,
)

FilesystemIndexRegistry = adapter.FilesystemIndexRegistry

__all__ = ["FilesystemIndexRegistry"]
