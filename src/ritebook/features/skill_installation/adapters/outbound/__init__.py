"""Outbound adapters for skill installation workflows."""

from .filesystem_installer import (
    FilesystemSkillInstallerAdapter,
)
from .index_registry_catalog import (
    IndexRegistrySkillCatalogAdapter,
)
from .json_installation_registry import (
    JsonInstallationRegistryAdapter,
)
from .json_lockfile import (
    JsonLockfileAdapter,
)
from .source_repository import (
    SourceRepositoryAdapter,
)
from .toml_requirements import (
    TomlRequirementsReader,
)

__all__ = [
    "FilesystemSkillInstallerAdapter",
    "IndexRegistrySkillCatalogAdapter",
    "JsonInstallationRegistryAdapter",
    "JsonLockfileAdapter",
    "SourceRepositoryAdapter",
    "TomlRequirementsReader",
]
