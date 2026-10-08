from __future__ import annotations

import hashlib
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
    AliasOrigin,
    IndexSourceType,
    RegisteredIndex,
)
from ritebook.features.publisher.adapters.outbound.json_index import JsonIndexWriter
from ritebook.features.publisher.domain import SkillCatalog
from ritebook.features.skill_installation.adapters.outbound import (
    FilesystemInstallationTransactionAdapter,
    FilesystemSkillInstallerAdapter,
    IndexRegistrySkillCatalogAdapter,
    JsonInstallationStateAdapter,
    SourceRepositoryAdapter,
    TomlRequirementsReader,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    InstallationWorkflow,
    OwnedInstallation,
    RegisteredSkillIndex,
    ResolvedSkillSource,
)
from ritebook.features.skill_linter.adapters.outbound.filesystem import (
    FilesystemSkillHeaderDiscovery,
)
from ritebook.features.skill_linter.adapters.outbound.publisher_precheck import (
    LinterPublisherPrecheck,
)
from ritebook.features.skill_linter.application.dtos import (
    LintSkillsResult,
    ValidatedSkill,
)
from ritebook.features.skill_linter.application.use_cases import (
    LintSkills,
    ValidateSkillHeaders,
)
from ritebook.shared_kernel import SKILL_FILE_NAME

if TYPE_CHECKING:
    from ritebook.features.skill_linter.application.dtos import LintSkillsCommand
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
    linter_result = FilesystemSkillHeaderDiscovery().discover_headers(str(skills_root))

    assert [file.relative_file for file in discovered_files] == [
        "alpha/SKILL.md",
        "zeta/SKILL.md",
    ]
    assert [header.expected_name for header in linter_result.headers] == [
        "alpha",
        "zeta",
    ]
    assert linter_result.discovered_skill_count == 2
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

    linter = LintSkills(
        header_discovery=FilesystemSkillHeaderDiscovery(),
        header_validator=ValidateSkillHeaders(),
    )
    entries = (
        LinterPublisherPrecheck(linter=linter)
        .run_prechecks(
            str(skills_root),
        )
        .skills
    )
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
        index_digest=published.index_digest,
        cache_root=str(cache_root),
        preserve_path=None,
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
    assert [
        skill.name
        for skill in index_reader.read_skills(cached_path, published.index_digest)
    ] == [
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
    registered_local = RegisteredSkillIndex(
        name="company-skills",
        source=prepared_local.source,
        source_type=prepared_local.source_type.value,
        source_revision=prepared_local.source_revision,
        index_digest=(
            f"sha256:{hashlib.sha256(prepared_local.index_content).hexdigest()}"
        ),
        source_cache_path=prepared_local.source_cache_path,
        cached_index_path=str(repository.path / "ritebook-index.json"),
        index_schema_version=1,
    )
    with SourceRepositoryAdapter().open_source(registered_local) as resolved_local:
        assert resolved_local.source_revision == revision
        assert Path(resolved_local.repository_path, "ritebook-index.json").is_file()
    prepared_clone = GitSourceAdapter().prepare_source(
        repository.path.as_uri(),
        str(tmp_path / "cache"),
    )

    assert prepared_local.source_type is IndexSourceType.LOCAL_GIT_REPO
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
    requirements_file = tmp_path / "consumer" / "ritebook.toml"
    lockfile_path = tmp_path / "consumer" / "ritebook.lock"
    source = ResolvedSkillSource(
        source="git@example.com:company/skills.git",
        source_type="git_url",
        repository_path=str(repository),
        source_revision="a" * 40,
        index_digest=f"sha256:{'b' * 64}",
    )
    skill = InstallableSkill(
        name="code-review",
        path="code-review",
        skill_file="code-review/SKILL.md",
        description="Helps review code.",
    )

    installer = FilesystemSkillInstallerAdapter()
    planned_target = installer.plan_target(str(target))
    staged = installer.stage(source=source, skill=skill, target=planned_target)
    state = JsonInstallationStateAdapter()
    paths = state.sync_paths(
        requirements_file=str(requirements_file),
        lockfile_path=str(lockfile_path),
    )
    assert paths.lockfile_path is not None
    entry = _owned_installation(
        target=planned_target.canonical_target,
        installed_tree_digest=staged.installed_tree_digest,
    )
    ownership_file = state.ownership_file((entry,), paths.ownership_path)
    lockfile = state.lockfile(
        (entry,),
        (),
        paths.lockfile_path,
        requirements_file="ritebook.toml",
    )
    try:
        with FilesystemInstallationTransactionAdapter().open(
            lock_path=paths.lock_path,
            journal_path=paths.journal_path,
        ) as transaction:
            transaction.replace_tree(
                staged_path=staged.staged_path,
                target_path=planned_target.canonical_target,
                expected_digest=None,
            )
            transaction.commit_state((ownership_file, lockfile))
    finally:
        installer.cleanup_staged(staged)

    assert (target / "SKILL.md").is_file()
    assert (target / "guide.md").read_text(encoding="utf-8") == "# Review guide\n"
    assert state.read_ownership(paths.ownership_path) == (entry,)
    assert '"schema_version": 2' in lockfile_path.read_text(encoding="utf-8")
    assert '"state": "complete"' in lockfile_path.read_text(encoding="utf-8")


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
    cached_content = """
{
  "schema_version": 1,
  "index": {"name": "company-skills"},
  "generated_at": "2026-07-13T18:00:00Z",
  "skills_root": ".",
  "skills": [
    {
      "name": "code-review",
      "path": "code-review",
      "skill_file": "code-review/SKILL.md",
      "description": "Helps review code changes."
    }
  ]
}
""".lstrip().encode()
    cached_index_path.write_bytes(cached_content)
    index_digest = f"sha256:{hashlib.sha256(cached_content).hexdigest()}"
    registry = FilesystemIndexRegistry()
    registry.upsert(
        _registered_index(
            cached_index_path=str(cached_index_path),
            index_digest=index_digest,
        ),
        str(registry_path),
    )
    catalog = IndexRegistrySkillCatalogAdapter(
        registry=registry,
        index_reader=JsonIndexReader(),
    )

    requirements = TomlRequirementsReader().read_requirements(str(requirements_file))
    index = catalog.get_index("company-skills", str(registry_path))
    assert index is not None
    skills = catalog.read_skills(str(cached_index_path), index.index_digest)

    assert requirements.targets == {"claude": ".claude/skills"}
    assert requirements.skills[0].name == "company-skills/code-review"
    assert index.cached_index_path == str(cached_index_path)
    assert skills == (
        InstallableSkill(
            name="code-review",
            path="code-review",
            skill_file="code-review/SKILL.md",
            description="Helps review code changes.",
        ),
    )


def test_linter_publisher_precheck_adapter_maps_real_linter_result() -> None:
    precheck = LinterPublisherPrecheck(
        linter=_FakeLinter(
            LintSkillsResult.create(
                discovered_skill_count=1,
                issues=[],
                validated_skills=[
                    ValidatedSkill(
                        path="code-review",
                        name="code-review",
                        skill_file="code-review/SKILL.md",
                        description="Helps review code.",
                    ),
                ],
            ),
        ),
    )

    result = precheck.run_prechecks("/tmp/skills")

    assert result.checked_skill_count == 1
    assert result.issues == ()
    assert [skill.path for skill in result.skills] == ["code-review"]


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
        alias_origin=AliasOrigin.PUBLISHED_NAME,
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


def _owned_installation(
    *,
    target: str,
    installed_tree_digest: str,
) -> OwnedInstallation:
    portable_target = ".claude/skills/code-review"
    return OwnedInstallation(
        workflow=InstallationWorkflow.SYNC,
        requirement="company-skills/code-review",
        index_name="company-skills",
        skill_name="code-review",
        target=portable_target,
        target_id=f"sha256:{hashlib.sha256(portable_target.encode()).hexdigest()}",
        canonical_target=target,
        source="git@example.com:company/skills.git",
        source_type="git_url",
        source_revision="a" * 40,
        index_digest=f"sha256:{'b' * 64}",
        index_schema_version=1,
        skill_path="code-review",
        skill_file="code-review/SKILL.md",
        installed_tree_digest=installed_tree_digest,
        target_ref="claude",
    )


class _FakeLinter:
    def __init__(self, result: LintSkillsResult) -> None:
        self.commands: list[LintSkillsCommand] = []
        self._result = result

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
        self.commands.append(command)
        return self._result
