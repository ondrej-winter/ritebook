from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ritebook.adapters.outbound.filesystem import discover_named_files
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
from ritebook.features.index_registry.application.dtos import (
    IndexSourceType,
    RegisteredIndex,
)
from ritebook.features.linter.adapters.outbound.filesystem import (
    FilesystemSkillHeaderDiscovery,
)
from ritebook.features.linter.adapters.outbound.publisher_precheck import (
    LinterPublisherPrecheck,
)
from ritebook.features.linter.application.dtos import LintSkillsResult
from ritebook.features.publisher.adapters.outbound.filesystem import (
    FilesystemSkillDiscovery,
)
from ritebook.features.publisher.adapters.outbound.json_index import JsonIndexWriter
from ritebook.features.publisher.domain import SkillCatalog
from ritebook.features.skill_installation.adapters.outbound import (
    FilesystemSkillInstallerAdapter,
    IndexRegistrySkillCatalogAdapter,
    JsonInstallationRegistryAdapter,
    JsonLockfileAdapter,
    SourceRepositoryAdapter,
    TomlRequirementsReader,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    InstallationManifestEntry,
    LockfileManifestEntry,
    RegisteredSkillIndex,
    ResolvedSkillSource,
)
from ritebook.shared_kernel import SKILL_FILE_NAME

if TYPE_CHECKING:
    from ritebook.features.linter.application.dtos import LintSkillsCommand
    from tests.integration.conftest import GitRepositoryFactory, SkillWriter


def test_filesystem_discovery_adapters_read_real_skill_files(
    skills_root: Path,
    write_valid_skill: SkillWriter,
) -> None:
    write_valid_skill("zeta", "Helps with zeta workflows.")
    write_valid_skill("alpha", "Helps with alpha workflows.")
    hidden_skill = skills_root / ".hidden" / "SKILL.md"
    hidden_skill.parent.mkdir(parents=True)
    hidden_skill.write_text("# Hidden\n", encoding="utf-8")

    discovered_files = discover_named_files(skills_root, file_name=SKILL_FILE_NAME)
    publisher_entries = FilesystemSkillDiscovery().discover_skills(str(skills_root))
    linter_result = FilesystemSkillHeaderDiscovery().discover_headers(str(skills_root))

    assert [file.relative_file for file in discovered_files] == [
        "alpha/SKILL.md",
        "zeta/SKILL.md",
    ]
    assert [(entry.name, entry.description) for entry in publisher_entries] == [
        ("alpha", "Helps with alpha workflows."),
        ("zeta", "Helps with zeta workflows."),
    ]
    assert [header.expected_name for header in linter_result.headers] == [
        "alpha",
        "zeta",
    ]
    assert linter_result.issues == ()


def test_publisher_json_index_and_index_registry_adapters_share_cacheable_index(
    tmp_path: Path,
    skills_root: Path,
    write_valid_skill: SkillWriter,
) -> None:
    write_valid_skill("code-review", "Helps review code changes.")
    write_valid_skill("test-driven-development", "Helps test first.")
    index_path = tmp_path / "published" / "ritebook-index.json"
    index_path.parent.mkdir()
    registry_path = tmp_path / "config" / "indexes.json"
    cache_root = tmp_path / "cache"

    entries = FilesystemSkillDiscovery().discover_skills(str(skills_root))
    catalog = SkillCatalog.create(
        index_name="company-skills",
        generated_at=datetime(2026, 7, 13, 18, 0, tzinfo=UTC),
        skills_root=".",
        skills=entries,
    )
    JsonIndexWriter().write_index(catalog, str(index_path))

    index_reader = JsonIndexReader()
    published = index_reader.read_index(index_path.read_bytes())
    cached_path = FilesystemIndexCache().write_index(
        name="company-skills",
        content=published.cacheable_content,
        cache_root=str(cache_root),
    )
    registry = FilesystemIndexRegistry()
    registry.upsert(
        _registered_index(
            source=str(index_path.parent),
            source_type=IndexSourceType.LOCAL_GIT_REPO,
            source_cache_path=None,
            cached_index_path=cached_path,
            skill_count=published.skill_count,
            index_digest=published.index_digest,
        ),
        str(registry_path),
    )

    assert published.published_name == "company-skills"
    assert [skill.name for skill in index_reader.read_skills(cached_path)] == [
        "code-review",
        "test-driven-development",
    ]
    assert registry.get("company-skills", str(registry_path)) == _registered_index(
        source=str(index_path.parent),
        source_type=IndexSourceType.LOCAL_GIT_REPO,
        source_cache_path=None,
        cached_index_path=cached_path,
        skill_count=2,
        index_digest=published.index_digest,
    )


def test_git_source_and_source_repository_adapters_resolve_real_git_revisions(
    tmp_path: Path,
    git_repository: GitRepositoryFactory,
) -> None:
    repository = git_repository(tmp_path / "published-index")
    (repository.path / "ritebook-index.json").write_text(
        '{"schema_version": 1, "index": {"name": "company-skills"}, "skills": []}\n',
        encoding="utf-8",
    )
    revision = repository.commit_all("Publish index")

    prepared_local = GitSourceAdapter().prepare_source(str(repository.path), None)
    resolved_local = SourceRepositoryAdapter().resolve_source(
        RegisteredSkillIndex(
            name="company-skills",
            source=prepared_local.source,
            source_type=prepared_local.source_type.value,
            source_cache_path=prepared_local.source_cache_path,
            cached_index_path=str(repository.path / "ritebook-index.json"),
            index_schema_version=1,
        ),
    )
    prepared_clone = GitSourceAdapter().prepare_source(
        repository.path.as_uri(),
        str(tmp_path / "cache"),
    )

    assert prepared_local.source_type is IndexSourceType.LOCAL_GIT_REPO
    assert resolved_local.source_revision == revision
    assert prepared_clone.source_type is IndexSourceType.GIT_URL
    assert Path(prepared_clone.repository_path, "ritebook-index.json").is_file()


def test_installation_adapters_copy_skill_and_write_persistent_state(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill_dir = repository / "code-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# code-review\n", encoding="utf-8")
    (skill_dir / "guide.md").write_text("# Review guide\n", encoding="utf-8")
    target = tmp_path / "consumer" / ".claude" / "skills" / "code-review"
    registry_path = tmp_path / "config" / "installations.json"
    lockfile_path = tmp_path / "consumer" / "ritebook.lock"
    source = ResolvedSkillSource(
        source=str(repository),
        source_type="local_git_repo",
        repository_path=str(repository),
        source_revision="abc123",
    )
    skill = InstallableSkill(
        name="code-review",
        path="code-review",
        skill_file="code-review/SKILL.md",
    )

    FilesystemSkillInstallerAdapter().install(
        source=source,
        skill=skill,
        target=str(target),
        force=False,
    )
    JsonInstallationRegistryAdapter().write_installation(
        _installation_entry(target=str(target), source=str(repository)),
        str(registry_path),
        force=False,
    )
    JsonLockfileAdapter().write_lockfile(
        (_lockfile_entry(source=str(repository)),),
        str(lockfile_path),
        requirements_file="ritebook.toml",
    )

    assert (target / "SKILL.md").is_file()
    assert (target / "guide.md").read_text(encoding="utf-8") == "# Review guide\n"
    assert '"installations"' in registry_path.read_text(encoding="utf-8")
    assert '"skills"' in lockfile_path.read_text(encoding="utf-8")


def test_requirements_and_catalog_bridge_adapters_read_real_registry_and_index(
    tmp_path: Path,
) -> None:
    requirements_file = tmp_path / "ritebook.toml"
    cached_index_path = tmp_path / "cache" / "ritebook-index.json"
    registry_path = tmp_path / "config" / "indexes.json"
    requirements_file.write_text(
        """
[targets]
claude = ".claude/skills"

[[skills]]
name = "company-skills/code-review"
target = "claude"
""".lstrip(),
        encoding="utf-8",
    )
    cached_index_path.parent.mkdir(parents=True)
    cached_index_path.write_text(
        """
{
  "schema_version": 1,
  "index": {"name": "company-skills"},
  "skills": [
    {
      "name": "code-review",
      "path": "code-review",
      "skill_file": "code-review/SKILL.md",
      "description": "Helps review code changes."
    }
  ]
}
""".lstrip(),
        encoding="utf-8",
    )
    registry = FilesystemIndexRegistry()
    registry.upsert(
        _registered_index(cached_index_path=str(cached_index_path)),
        str(registry_path),
    )
    catalog = IndexRegistrySkillCatalogAdapter(
        registry=registry,
        index_reader=JsonIndexReader(),
    )

    requirements = TomlRequirementsReader().read_requirements(str(requirements_file))
    index = catalog.get_index("company-skills", str(registry_path))
    skills = catalog.read_skills(str(cached_index_path))

    assert requirements.targets == {"claude": ".claude/skills"}
    assert requirements.skills[0].name == "company-skills/code-review"
    assert index is not None
    assert index.cached_index_path == str(cached_index_path)
    assert skills == (
        InstallableSkill(
            name="code-review",
            path="code-review",
            skill_file="code-review/SKILL.md",
        ),
    )


def test_linter_publisher_precheck_adapter_maps_real_linter_result() -> None:
    precheck = LinterPublisherPrecheck(
        linter=_FakeLinter(
            LintSkillsResult.create(
                validated_skill_count=1,
                issues=[],
            ),
        ),
    )

    result = precheck.run_prechecks("/tmp/skills")

    assert result.checked_skill_count == 1
    assert result.issues == ()


def _registered_index(
    *,
    source: str = "git@example.com:company/skills.git",
    source_type: IndexSourceType = IndexSourceType.GIT_URL,
    source_cache_path: str | None = "/cache/git/source-id",
    cached_index_path: str = "/cache/indexes/company-skills/ritebook-index.json",
    skill_count: int = 1,
    source_revision: str = "a" * 40,
    index_digest: str = f"sha256:{'b' * 64}",
) -> RegisteredIndex:
    return RegisteredIndex(
        name="company-skills",
        published_name="company-skills",
        source=source,
        source_type=source_type,
        source_revision=source_revision,
        index_digest=index_digest,
        source_cache_path=source_cache_path,
        cached_index_path=cached_index_path,
        source_schema_version=1,
        skill_count=skill_count,
        added_at="2026-07-13T18:00:00Z",
        updated_at="2026-07-13T18:00:00Z",
    )


def _installation_entry(*, target: str, source: str) -> InstallationManifestEntry:
    return InstallationManifestEntry(
        requirement="company-skills/code-review",
        index_name="company-skills",
        skill_name="code-review",
        target=target,
        source=source,
        source_type="local_git_repo",
        source_revision="abc123",
        index_schema_version=1,
        skill_path="code-review",
        skill_file="code-review/SKILL.md",
        installed_at="2026-07-13T18:00:00Z",
    )


def _lockfile_entry(*, source: str) -> LockfileManifestEntry:
    return LockfileManifestEntry(
        requirement="company-skills/code-review",
        index_name="company-skills",
        skill_name="code-review",
        target=".claude/skills/code-review",
        source=source,
        source_type="local_git_repo",
        source_revision="abc123",
        index_schema_version=1,
        skill_path="code-review",
        skill_file="code-review/SKILL.md",
        locked_at="2026-07-13T18:00:00Z",
        target_ref="claude",
    )


class _FakeLinter:
    def __init__(self, result: LintSkillsResult) -> None:
        self.commands: list[LintSkillsCommand] = []
        self._result = result

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
        self.commands.append(command)
        return self._result
