"""Index-registry-backed skill catalog adapter exports.

This package owns the approved cross-slice bridge from published index-registry
application ports into skill-installation DTOs. Keep index-registry adapter,
use-case, and private implementation imports out of this boundary.
"""

from . import adapter

IndexRegistrySkillCatalogAdapter = adapter.IndexRegistrySkillCatalogAdapter

__all__ = ["IndexRegistrySkillCatalogAdapter"]
