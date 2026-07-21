from collections.abc import Iterator
from contextlib import contextmanager

from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    InstallationManifestEntry,
    LockfileManifestEntry,
    RegisteredSkillIndex,
    ResolvedSkillSource,
    SkillRequirements,
)


class FakeSkillCatalog:
    def __init__(
        self,
        *,
        indexes: list[RegisteredSkillIndex] | None = None,
        skills_by_path: dict[str, tuple[InstallableSkill, ...]] | None = None,
    ) -> None:
        self.indexes = {entry.name: entry for entry in indexes or []}
        self.skills_by_path = skills_by_path or {}
        self.get_index_calls: list[tuple[str, str | None]] = []
        self.read_skills_calls: list[str] = []

    def get_index(
        self,
        name: str,
        registry_path: str | None,
    ) -> RegisteredSkillIndex | None:
        self.get_index_calls.append((name, registry_path))
        return self.indexes.get(name)

    def read_skills(self, cached_index_path: str) -> tuple[InstallableSkill, ...]:
        self.read_skills_calls.append(cached_index_path)
        return self.skills_by_path.get(cached_index_path, ())


class FakeSkillSourceResolver:
    def __init__(
        self,
        source: ResolvedSkillSource | None = None,
        *,
        failure: Exception | None = None,
    ) -> None:
        self.source = source or ResolvedSkillSource(
            source="git@example.com:company/skills.git",
            source_type="git_url",
            repository_path="/cache/git/company-skills",
            source_revision="c" * 40,
        )
        self.failure = failure
        self.resolve_calls: list[RegisteredSkillIndex] = []

    @contextmanager
    def open_source(self, index: RegisteredSkillIndex) -> Iterator[ResolvedSkillSource]:
        self.resolve_calls.append(index)
        if self.failure is not None:
            raise self.failure
        yield self.source


class FakeSkillInstaller:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.install_calls: list[
            tuple[ResolvedSkillSource, InstallableSkill, str, bool]
        ] = []

    def install(
        self,
        *,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
        target: str,
        force: bool,
    ) -> None:
        self.install_calls.append((source, skill, target, force))
        if self.failure is not None:
            raise self.failure


class FakeInstallationManifest:
    def __init__(self) -> None:
        self.write_calls: list[tuple[InstallationManifestEntry, str | None, bool]] = []
        self.lockfile_write_calls: list[
            tuple[tuple[LockfileManifestEntry, ...], str | None, str]
        ] = []

    def write_installation(
        self,
        entry: InstallationManifestEntry,
        registry_path: str | None,
        *,
        force: bool,
    ) -> None:
        self.write_calls.append((entry, registry_path, force))

    def write_lockfile(
        self,
        entries: tuple[LockfileManifestEntry, ...],
        lockfile_path: str | None,
        *,
        requirements_file: str,
    ) -> None:
        self.lockfile_write_calls.append((entries, lockfile_path, requirements_file))


class FakeRequirementsReader:
    def __init__(self, requirements: SkillRequirements) -> None:
        self.requirements = requirements
        self.read_calls: list[str] = []

    def read_requirements(self, requirements_file: str) -> SkillRequirements:
        self.read_calls.append(requirements_file)
        return self.requirements


def registered_skill_index(
    *,
    name: str = "company-skills",
    source: str = "git@example.com:company/skills.git",
    source_type: str = "git_url",
    source_revision: str = "a" * 40,
    index_digest: str = f"sha256:{'b' * 64}",
    source_cache_path: str | None = "/cache/git/company-skills",
    cached_index_path: str = "/cache/indexes/company-skills/ritebook-index.json",
    index_schema_version: int = 1,
) -> RegisteredSkillIndex:
    return RegisteredSkillIndex(
        name=name,
        source=source,
        source_type=source_type,
        source_revision=source_revision,
        index_digest=index_digest,
        source_cache_path=source_cache_path,
        cached_index_path=cached_index_path,
        index_schema_version=index_schema_version,
    )


def installable_skill(
    *,
    name: str = "code-review",
    path: str | None = None,
    skill_file: str | None = None,
    source_root: str = "skills",
) -> InstallableSkill:
    skill_path = path or name
    return InstallableSkill(
        name=name,
        path=skill_path,
        skill_file=skill_file or f"{skill_path}/SKILL.md",
        source_root=source_root,
    )
