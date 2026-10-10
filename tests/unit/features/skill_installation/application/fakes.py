from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    RegisteredSkillIndex,
)


def registered_skill_index(
    *,
    name: str = "company-skills",
    source: str = "git@example.com:company/skills.git",
    source_type: str = "git_url",
    source_revision: str = "a" * 40,
    source_branch: str = "refs/heads/main",
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
        source_branch=source_branch,
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
    description: str | None = None,
    source_root: str = "skills",
) -> InstallableSkill:
    skill_path = path or name
    return InstallableSkill(
        name=name,
        path=skill_path,
        skill_file=skill_file or f"{skill_path}/SKILL.md",
        description=description or f"Helps with {name} workflows.",
        source_root=source_root,
    )
