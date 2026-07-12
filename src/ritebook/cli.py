"""Ritebook command-line entry point and composition root."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.adapters.inbound.cli import run
from ritebook.features.index_registry.adapters.outbound.filesystem_registry import (
    FilesystemIndexRegistry,
)
from ritebook.features.index_registry.adapters.outbound.git import GitSourceAdapter
from ritebook.features.index_registry.adapters.outbound.index_cache import (
    FilesystemIndexCache,
)
from ritebook.features.index_registry.adapters.outbound.json_index import (
    JsonIndexReader,
)
from ritebook.features.index_registry.application.use_cases import (
    AddIndex,
    ListIndexes,
    ListSkills,
    UpdateIndex,
)
from ritebook.features.linter.adapters.outbound.filesystem import (
    FilesystemSkillHeaderDiscovery,
)
from ritebook.features.linter.adapters.outbound.publisher_precheck import (
    LinterPublisherPrecheck,
)
from ritebook.features.linter.application.use_cases import (
    LintSkills,
    ValidateSkillHeaders,
)
from ritebook.features.publisher.adapters.outbound.filesystem import (
    FilesystemSkillDiscovery,
)
from ritebook.features.publisher.adapters.outbound.json_index import JsonIndexWriter
from ritebook.features.publisher.application.use_cases import PublishIndex
from ritebook.features.skill_installation.adapters.outbound import (
    FilesystemSkillInstallerAdapter,
    IndexRegistrySkillCatalogAdapter,
    JsonInstallationRegistryAdapter,
    JsonLockfileAdapter,
    SourceRepositoryAdapter,
    TomlRequirementsReader,
)
from ritebook.features.skill_installation.application.use_cases import (
    InstallFromRequirements,
    InstallSkill,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Ritebook command-line interface."""
    linter = LintSkills(
        header_discovery=FilesystemSkillHeaderDiscovery(),
        header_validator=ValidateSkillHeaders(),
    )
    publisher = PublishIndex(
        skill_discovery=FilesystemSkillDiscovery(),
        precheck=LinterPublisherPrecheck(linter=linter),
        index_writer=JsonIndexWriter(),
        clock=lambda: datetime.now(UTC),
    )
    registry = FilesystemIndexRegistry()
    cache = FilesystemIndexCache()
    git_source = GitSourceAdapter()
    index_reader = JsonIndexReader()
    add_index = AddIndex(
        git_source=git_source,
        index_reader=index_reader,
        registry=registry,
        cache=cache,
        clock=lambda: datetime.now(UTC),
    )
    list_indexes = ListIndexes(registry=registry)
    list_skills = ListSkills(registry=registry, cached_index_reader=index_reader)
    update_index = UpdateIndex(
        git_source=git_source,
        index_reader=index_reader,
        registry=registry,
        cache=cache,
        clock=lambda: datetime.now(UTC),
    )
    installation_catalog = IndexRegistrySkillCatalogAdapter(
        registry=registry,
        index_reader=index_reader,
    )
    source_repository = SourceRepositoryAdapter()
    skill_installer = FilesystemSkillInstallerAdapter()
    install_skill = InstallSkill(
        catalog=installation_catalog,
        source_resolver=source_repository,
        installer=skill_installer,
        manifest=JsonInstallationRegistryAdapter(),
        clock=lambda: datetime.now(UTC),
    )
    install_from_requirements = InstallFromRequirements(
        requirements_reader=TomlRequirementsReader(),
        catalog=installation_catalog,
        source_resolver=source_repository,
        installer=skill_installer,
        manifest=JsonLockfileAdapter(),
        clock=lambda: datetime.now(UTC),
    )
    return run(
        argv,
        linter=linter,
        publisher=publisher,
        add_index=add_index,
        list_indexes=list_indexes,
        list_skills=list_skills,
        update_index=update_index,
        install_skill=install_skill,
        install_from_requirements=install_from_requirements,
    )
