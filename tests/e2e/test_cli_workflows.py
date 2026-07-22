from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from tests.e2e.conftest import (
        CliRunner,
        GitRepository,
        GitRepositoryFactory,
        InvalidSkillWriter,
        SkillWriter,
    )


def test_publisher_to_consumer_workflow_uses_local_git_cache(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    index_name = "company-skills"

    write_valid_skill("alpha", "Helps with alpha workflows.")
    collected_skill = skills_root / "browser" / "beta" / "SKILL.md"
    collected_skill.parent.mkdir(parents=True)
    collected_skill.write_text(
        _valid_skill_content("beta", "Helps with beta workflows."),
        encoding="utf-8",
    )

    lint_result = run_cli(["lint-skills", "--skills-root", str(skills_root)])
    lint_result.assert_success()
    assert lint_result.stdout == "Validated 2 skill(s)\n"

    published_skills_root = published_repo.path / "skills"
    _copy_skill_directories_to_repository(skills_root, published_skills_root)
    publish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(published_skills_root),
            "--index-name",
            index_name,
        ],
        cwd=published_repo.path,
    )
    publish_result.assert_success()
    assert publish_result.stdout == (
        "Published skill index with 2 skill(s) to ritebook-index.json\n"
    )
    assert (published_repo.path / "ritebook-index.json").is_file()
    assert _read_json(published_repo.path / "ritebook-index.json")["skills_root"] == (
        "skills"
    )
    published_repo.commit_all("Publish initial skill index")

    add_result = run_cli(
        [
            "add-index",
            "--source",
            str(published_repo.path),
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )
    add_result.assert_success()
    assert add_result.stdout == "Added index company-skills with 2 skill(s)\n"

    initial_list = run_cli(
        ["list-skills", "--registry-path", str(registry_path), "--show-description"],
    )
    initial_list.assert_success()
    assert initial_list.stdout == (
        "Indexes\n"
        "└── company-skills\n"
        "    ├── alpha — Helps with alpha workflows.\n"
        "    └── browser/beta — Helps with beta workflows.\n"
    )

    write_valid_skill("gamma", "Helps with gamma workflows.")
    _copy_skill_directories_to_repository(skills_root, published_skills_root)
    republish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(published_skills_root),
            "--index-name",
            index_name,
        ],
        cwd=published_repo.path,
    )
    republish_result.assert_success()
    assert republish_result.stdout == (
        "Published skill index with 3 skill(s) to ritebook-index.json\n"
    )
    published_repo.commit_all("Publish refreshed skill index")

    update_result = run_cli(
        [
            "update-index",
            "--name",
            index_name,
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )
    update_result.assert_success()
    assert update_result.stdout == "Updated index company-skills with 3 skill(s)\n"

    updated_list = run_cli(
        ["list-skills", "--registry-path", str(registry_path), "--show-description"],
    )
    updated_list.assert_success()
    assert updated_list.stdout == (
        "Indexes\n"
        "└── company-skills\n"
        "    ├── alpha — Helps with alpha workflows.\n"
        "    ├── browser/beta — Helps with beta workflows.\n"
        "    └── gamma — Helps with gamma workflows.\n"
    )


def test_empty_registry_browsing_commands_report_empty_state(
    run_cli: CliRunner,
    registry_path: Path,
) -> None:
    list_indexes = run_cli(["list-indexes", "--registry-path", str(registry_path)])
    list_skills = run_cli(["list-skills", "--registry-path", str(registry_path)])

    list_indexes.assert_success()
    assert list_indexes.stdout == "No indexes registered\n"
    assert list_indexes.stderr == ""
    list_skills.assert_success()
    assert list_skills.stdout == "No skills found\n"
    assert list_skills.stderr == ""


def test_registry_browsing_supports_index_listing_and_filtered_skill_listing(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")

    write_valid_skill("alpha", "Helps with alpha workflows.")
    write_valid_skill("beta", "Helps with beta workflows.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
    )

    list_indexes = run_cli(["list-indexes", "--registry-path", str(registry_path)])
    list_skills = run_cli(
        [
            "list-skills",
            "--index-name",
            "company-skills",
            "--registry-path",
            str(registry_path),
        ],
    )

    list_indexes.assert_success()
    list_indexes_fields = list_indexes.stdout.rstrip("\n").split("\t")
    assert list_indexes_fields == [
        "company-skills",
        "2 skill(s)",
        "local_git_repo",
        list_indexes_fields[3],
        str(published_repo.path),
    ]
    assert list_indexes.stderr == ""
    list_skills.assert_success()
    assert list_skills.stdout == (
        "Indexes\n└── company-skills\n    ├── alpha\n    └── beta\n"
    )
    assert list_skills.stderr == ""


def test_add_index_alias_force_replace_and_update_all_happy_path(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    platform_repo = git_repository(tmp_path / "platform-index")
    data_repo = git_repository(tmp_path / "data-index")

    write_valid_skill("review", "Helps review changes.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=platform_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
        alias="platform-skills",
    )

    write_valid_skill("query-helper", "Helps query data.")
    data_skills_root = data_repo.path / "skills"
    _copy_skill_directories_to_repository(skills_root, data_skills_root)
    publish_data = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(data_skills_root),
            "--index-name",
            "data-skills",
        ],
        cwd=data_repo.path,
    )
    publish_data.assert_success()
    data_repo.commit_all("Publish data index")

    replace_result = run_cli(
        [
            "add-index",
            "--source",
            str(data_repo.path),
            "--alias",
            "platform-skills",
            "--force",
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )
    replace_result.assert_success()
    assert replace_result.stdout == "Added index platform-skills with 2 skill(s)\n"

    write_valid_skill("chart-builder", "Helps build charts.")
    _copy_skill_directories_to_repository(skills_root, data_skills_root)
    republish_data = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(data_skills_root),
            "--index-name",
            "data-skills",
        ],
        cwd=data_repo.path,
    )
    republish_data.assert_success()
    data_repo.commit_all("Refresh data index")

    update_all = run_cli(
        [
            "update-index",
            "--all",
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )

    update_all.assert_success()
    assert update_all.stdout == "Updated 1 index(es) with 3 total skill(s)\n"
    assert update_all.stderr == ""
    listed = run_cli(
        ["list-skills", "--registry-path", str(registry_path), "--show-description"],
    )
    listed.assert_success()
    assert listed.stdout == (
        "Indexes\n"
        "└── platform-skills\n"
        "    ├── chart-builder — Helps build charts.\n"
        "    ├── query-helper — Helps query data.\n"
        "    └── review — Helps review changes.\n"
    )


def test_lint_skills_reports_invalid_metadata_failure(
    run_cli: CliRunner,
    skills_root: Path,
    write_invalid_skill: InvalidSkillWriter,
) -> None:
    write_invalid_skill("missing-description")

    result = run_cli(["lint-skills", "--skills-root", str(skills_root)])

    result.assert_failure()
    assert result.stdout == ""
    assert result.stderr == ("missing-description/SKILL.md: description is required.\n")


def test_catalog_commands_reject_over_deep_and_mixed_skill_nodes(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    git_repository: GitRepositoryFactory,
) -> None:
    over_deep_skill = skills_root / "quality" / "python" / "review" / "SKILL.md"
    over_deep_skill.parent.mkdir(parents=True)
    over_deep_skill.write_text(
        _valid_skill_content("review", "Helps review Python changes."),
        encoding="utf-8",
    )

    lint_result = run_cli(["lint-skills", "--skills-root", str(skills_root)])

    lint_result.assert_failure()
    assert lint_result.stdout == ""
    assert "quality/python/review/SKILL.md" in lint_result.stderr
    assert "one or two segments" in lint_result.stderr

    shutil.rmtree(skills_root)
    root_skill = skills_root / "quality" / "SKILL.md"
    child_skill = skills_root / "quality" / "review" / "SKILL.md"
    root_skill.parent.mkdir(parents=True)
    child_skill.parent.mkdir(parents=True)
    root_skill.write_text(
        _valid_skill_content("quality", "Helps with quality workflows."),
        encoding="utf-8",
    )
    child_skill.write_text(
        _valid_skill_content("review", "Helps review changes."),
        encoding="utf-8",
    )
    published_repo = git_repository(tmp_path / "published-index")
    published_skills_root = published_repo.path / "skills"
    _copy_skill_directories_to_repository(skills_root, published_skills_root)

    publish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(published_skills_root),
            "--index-name",
            "company-skills",
        ],
        cwd=published_repo.path,
    )

    publish_result.assert_failure()
    assert publish_result.stdout == ""
    assert "cannot be both a root skill and a collection" in publish_result.stderr
    assert not (published_repo.path / "ritebook-index.json").exists()


def test_update_index_preserves_cached_catalog_after_invalid_candidate(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    write_valid_skill("code-review", "Helps review code changes.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
    )
    before_registry = registry_path.read_bytes()
    registry_data = _read_json(registry_path)
    cached_index = Path(registry_data["indexes"][0]["cached_index_path"])
    before_cache = cached_index.read_bytes()

    candidate = _read_json(published_repo.path / "ritebook-index.json")
    candidate["skills"].append(
        {
            "name": "deep-review",
            "path": "quality/python/deep-review",
            "skill_file": "quality/python/deep-review/SKILL.md",
            "description": "Helps review deeply nested changes.",
        },
    )
    (published_repo.path / "ritebook-index.json").write_text(
        f"{json.dumps(candidate, indent=2)}\n",
        encoding="utf-8",
    )
    published_repo.commit_all("Publish invalid candidate index")

    update_result = run_cli(
        [
            "update-index",
            "--name",
            "company-skills",
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )

    update_result.assert_failure()
    assert "invalid schema-v1 catalog structure" in update_result.stderr
    assert "reorganize skills into root or collection/skill paths" in (
        update_result.stderr.lower()
    )
    assert registry_path.read_bytes() == before_registry
    assert cached_index.read_bytes() == before_cache
    listed = run_cli(["list-skills", "--registry-path", str(registry_path)])
    listed.assert_success()
    assert listed.stdout == "Indexes\n└── company-skills\n    └── code-review\n"


def test_install_skill_copies_cached_skill_directory_and_writes_installation_state(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    index_name = "company-skills"
    target = tmp_path / "consumer" / ".claude" / "skills" / "code-review"
    installation_registry_path = tmp_path / "config" / "installations.json"

    write_valid_skill("code-review", "Helps review code changes.")
    (skills_root / "code-review" / "checklist.md").write_text(
        "# Review checklist\n",
        encoding="utf-8",
    )
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name=index_name,
        registry_path=registry_path,
        cache_root=cache_root,
    )

    result = run_cli(
        [
            "install-skill",
            "company-skills/code-review",
            "--target",
            str(target),
            "--registry-path",
            str(registry_path),
            "--installation-registry-path",
            str(installation_registry_path),
        ],
    )

    result.assert_success()
    assert result.stdout == f"Installed company-skills/code-review to {target}\n"
    assert (target / "SKILL.md").is_file()
    assert (target / "checklist.md").read_text(encoding="utf-8") == (
        "# Review checklist\n"
    )
    installation_registry = _read_json(installation_registry_path)
    assert installation_registry["schema_version"] == 1
    assert installation_registry["installations"] == [
        {
            "requirement": "company-skills/code-review",
            "index_name": "company-skills",
            "skill_name": "code-review",
            "target": str(target.resolve()),
            "source": str(published_repo.path),
            "source_type": "local_git_repo",
            "source_revision": _git_head(published_repo.path),
            "index_digest": installation_registry["installations"][0]["index_digest"],
            "index_schema_version": 1,
            "skill_path": "skills/code-review",
            "skill_file": "skills/code-review/SKILL.md",
            "installed_at": installation_registry["installations"][0]["installed_at"],
        },
    ]


def test_install_skill_copies_skill_from_subdirectory_and_records_source_path(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    target = tmp_path / "consumer" / ".claude" / "skills" / "code-review"
    installation_registry_path = tmp_path / "config" / "installations.json"

    skill_file = skills_root / "skills" / "code-review" / "SKILL.md"
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(
        _valid_skill_content("code-review", "Helps review code changes."),
        encoding="utf-8",
    )
    (skills_root / "skills" / "code-review" / "checklist.md").write_text(
        "# Nested review checklist\n",
        encoding="utf-8",
    )
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
    )

    result = run_cli(
        [
            "install-skill",
            "company-skills/skills/code-review",
            "--target",
            str(target),
            "--registry-path",
            str(registry_path),
            "--installation-registry-path",
            str(installation_registry_path),
        ],
    )

    result.assert_success()
    assert result.stdout == f"Installed company-skills/skills/code-review to {target}\n"
    assert (target / "SKILL.md").is_file()
    assert (target / "checklist.md").read_text(encoding="utf-8") == (
        "# Nested review checklist\n"
    )
    installation_registry = _read_json(installation_registry_path)
    assert installation_registry["installations"][0]["requirement"] == (
        "company-skills/skills/code-review"
    )
    assert installation_registry["installations"][0]["skill_path"] == (
        "skills/skills/code-review"
    )
    assert installation_registry["installations"][0]["skill_file"] == (
        "skills/skills/code-review/SKILL.md"
    )


def test_install_skill_refuses_existing_target_without_force(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    target = tmp_path / "consumer" / ".claude" / "skills" / "code-review"
    target.mkdir(parents=True)
    (target / "local-note.md").write_text("keep me\n", encoding="utf-8")

    write_valid_skill("code-review", "Helps review code changes.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
    )

    result = run_cli(
        [
            "install-skill",
            "company-skills/code-review",
            "--target",
            str(target),
            "--registry-path",
            str(registry_path),
            "--installation-registry-path",
            str(tmp_path / "config" / "installations.json"),
        ],
    )

    result.assert_failure()
    assert result.stdout == ""
    expected_error = (
        f"ritebook: error: target {target} already exists; use --force to replace it\n"
    )
    assert result.stderr == expected_error
    assert (target / "local-note.md").read_text(encoding="utf-8") == "keep me\n"


def test_install_skill_force_replaces_existing_target_and_recorded_state(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    target = tmp_path / "consumer" / ".claude" / "skills" / "code-review"
    installation_registry_path = tmp_path / "config" / "installations.json"
    target.mkdir(parents=True)
    (target / "stale.md").write_text("remove me\n", encoding="utf-8")

    write_valid_skill("code-review", "Helps review code changes.")
    (skills_root / "code-review" / "fresh.md").write_text(
        "# Fresh content\n",
        encoding="utf-8",
    )
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
    )

    result = run_cli(
        [
            "install-skill",
            "company-skills/code-review",
            "--target",
            str(target),
            "--force",
            "--registry-path",
            str(registry_path),
            "--installation-registry-path",
            str(installation_registry_path),
        ],
    )

    result.assert_success()
    assert result.stdout == f"Installed company-skills/code-review to {target}\n"
    assert not (target / "stale.md").exists()
    assert (target / "fresh.md").read_text(encoding="utf-8") == "# Fresh content\n"
    installation_registry = _read_json(installation_registry_path)
    assert installation_registry["installations"][0]["target"] == str(target.resolve())


def test_install_reads_requirements_file_and_writes_lockfile(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    consumer_repo = tmp_path / "consumer"
    requirements_file = consumer_repo / "ritebook.toml"
    lockfile = consumer_repo / "ritebook.lock"

    write_valid_skill("code-review", "Helps review code changes.")
    write_valid_skill("test-driven-development", "Helps test first.")
    (skills_root / "test-driven-development" / "notes.md").write_text(
        "# TDD notes\n",
        encoding="utf-8",
    )
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
        portable_source=True,
    )
    consumer_repo.mkdir()
    requirements_file.write_text(
        """
[targets]
claude = ".claude/skills"

[[skills]]
name = "company-skills/code-review"
target = "claude"

[[skills]]
name = "company-skills/test-driven-development"
target_path = ".agents/skills/tdd"
""".lstrip(),
        encoding="utf-8",
    )

    result = run_cli(
        [
            "install",
            "--file",
            str(requirements_file),
            "--registry-path",
            str(registry_path),
            "--lockfile",
            str(lockfile),
        ],
        cwd=consumer_repo,
    )

    result.assert_success()
    assert result.stdout == f"Installed 2 skill(s) from {requirements_file}\n"
    assert (consumer_repo / ".claude" / "skills" / "code-review" / "SKILL.md").is_file()
    assert (consumer_repo / ".agents" / "skills" / "tdd" / "notes.md").read_text(
        encoding="utf-8",
    ) == "# TDD notes\n"
    lockfile_data = _read_json(lockfile)
    assert lockfile_data["schema_version"] == 1
    assert lockfile_data["requirements_file"] == str(requirements_file)
    assert [entry["requirement"] for entry in lockfile_data["skills"]] == [
        "company-skills/code-review",
        "company-skills/test-driven-development",
    ]
    assert lockfile_data["skills"][0] == {
        "requirement": "company-skills/code-review",
        "index_name": "company-skills",
        "skill_name": "code-review",
        "target": ".claude/skills/code-review",
        "source": published_repo.path.as_uri(),
        "source_type": "git_url",
        "index_digest": lockfile_data["skills"][0]["index_digest"],
        "index_schema_version": 1,
        "skill_path": "skills/code-review",
        "skill_file": "skills/code-review/SKILL.md",
        "locked_at": lockfile_data["skills"][0]["locked_at"],
        "target_ref": "claude",
        "source_revision": _git_head(published_repo.path),
    }
    assert lockfile_data["skills"][1]["target"] == ".agents/skills/tdd"
    assert "target_ref" not in lockfile_data["skills"][1]


def test_install_expands_collection_but_install_skill_keeps_exact_selection(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    consumer_repo = tmp_path / "consumer"
    requirements_file = consumer_repo / "ritebook.toml"
    lockfile = consumer_repo / "ritebook.lock"
    installation_registry = tmp_path / "config" / "installations.json"
    direct_target = consumer_repo / ".direct" / "browser"

    for name, description in (
        ("alpha-tool", "Helps with alpha browser workflows."),
        ("zeta-tool", "Helps with zeta browser workflows."),
    ):
        skill_file = skills_root / "browser" / name / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text(
            _valid_skill_content(name, description),
            encoding="utf-8",
        )
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
        portable_source=True,
    )
    consumer_repo.mkdir()
    requirements_file.write_text(
        """
[targets]
agents = ".agents/skills"

[[skills]]
name = "company-skills/browser"
target = "agents"
""".lstrip(),
        encoding="utf-8",
    )

    install_result = run_cli(
        [
            "install",
            "--file",
            str(requirements_file),
            "--registry-path",
            str(registry_path),
            "--lockfile",
            str(lockfile),
        ],
        cwd=consumer_repo,
    )

    install_result.assert_success()
    assert install_result.stdout == f"Installed 2 skill(s) from {requirements_file}\n"
    assert (consumer_repo / ".agents" / "skills" / "alpha-tool" / "SKILL.md").is_file()
    assert (consumer_repo / ".agents" / "skills" / "zeta-tool" / "SKILL.md").is_file()
    lockfile_data = _read_json(lockfile)
    assert [entry["requirement"] for entry in lockfile_data["skills"]] == [
        "company-skills/browser/alpha-tool",
        "company-skills/browser/zeta-tool",
    ]
    assert [entry["skill_path"] for entry in lockfile_data["skills"]] == [
        "skills/browser/alpha-tool",
        "skills/browser/zeta-tool",
    ]

    direct_result = run_cli(
        [
            "install-skill",
            "company-skills/browser",
            "--target",
            str(direct_target),
            "--registry-path",
            str(registry_path),
            "--installation-registry-path",
            str(installation_registry),
        ],
        cwd=consumer_repo,
    )

    direct_result.assert_failure()
    assert "unknown skill company-skills/browser" in direct_result.stderr.lower()
    assert not direct_target.exists()
    assert not installation_registry.exists()


def test_install_retains_copied_target_when_lockfile_commit_fails(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    consumer_repo = tmp_path / "consumer"
    requirements_file = consumer_repo / "ritebook.toml"
    target = consumer_repo / ".claude" / "skills" / "code-review"
    blocked_parent = consumer_repo / "blocked"
    lockfile = blocked_parent / "ritebook.lock"

    write_valid_skill("code-review", "Helps review code changes.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
        portable_source=True,
    )
    consumer_repo.mkdir()
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
    blocked_parent.write_text("not a directory\n", encoding="utf-8")

    result = run_cli(
        [
            "install",
            "--file",
            str(requirements_file),
            "--registry-path",
            str(registry_path),
            "--lockfile",
            str(lockfile),
        ],
        cwd=consumer_repo,
    )

    result.assert_failure()
    assert result.stdout == ""
    assert result.stderr == (
        "ritebook: error: installation copied target(s) "
        ".claude/skills/code-review, but ritebook.lock was not updated; copied "
        "directories remain, so inspect them and retry the installation\n"
    )
    assert (target / "SKILL.md").is_file()
    assert blocked_parent.read_text(encoding="utf-8") == "not a directory\n"
    assert not lockfile.exists()


def test_install_uses_default_requirements_and_lockfile_paths_with_force(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    consumer_repo = tmp_path / "consumer"
    requirements_file = consumer_repo / "ritebook.toml"
    lockfile = consumer_repo / "ritebook.lock"
    target = consumer_repo / ".claude" / "skills" / "code-review"

    write_valid_skill("code-review", "Helps review code changes.")
    (skills_root / "code-review" / "guide.md").write_text(
        "# Review guide\n",
        encoding="utf-8",
    )
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
        portable_source=True,
    )
    consumer_repo.mkdir()
    target.mkdir(parents=True)
    (target / "stale.md").write_text("remove me\n", encoding="utf-8")
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

    result = run_cli(
        ["install", "--force", "--registry-path", str(registry_path)],
        cwd=consumer_repo,
    )

    result.assert_success()
    assert result.stdout == "Installed 1 skill(s) from ritebook.toml\n"
    assert not (target / "stale.md").exists()
    assert (target / "guide.md").read_text(encoding="utf-8") == "# Review guide\n"
    lockfile_data = _read_json(lockfile)
    assert lockfile_data["requirements_file"] == "ritebook.toml"
    assert lockfile_data["skills"][0]["target"] == ".claude/skills/code-review"


def test_install_does_not_write_lockfile_when_requirements_are_invalid(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_repo = git_repository(tmp_path / "published-index")
    consumer_repo = tmp_path / "consumer"
    requirements_file = consumer_repo / "ritebook.toml"
    lockfile = consumer_repo / "ritebook.lock"

    write_valid_skill("code-review", "Helps review code changes.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        index_name="company-skills",
        registry_path=registry_path,
        cache_root=cache_root,
        portable_source=True,
    )
    consumer_repo.mkdir()
    requirements_file.write_text(
        """
[targets]
agents = ".agents/skills"

[[skills]]
name = "company-skills/code-review"
target = "claude"
""".lstrip(),
        encoding="utf-8",
    )

    result = run_cli(
        [
            "install",
            "--file",
            str(requirements_file),
            "--registry-path",
            str(registry_path),
            "--lockfile",
            str(lockfile),
        ],
        cwd=consumer_repo,
    )

    result.assert_failure()
    assert result.stdout == ""
    expected_error = (
        "ritebook: error: target nickname claude is not defined in "
        f"{requirements_file}\n"
    )
    assert result.stderr == expected_error
    assert not lockfile.exists()


def _publish_and_register_index(
    *,
    run_cli: CliRunner,
    published_repo: GitRepository,
    skills_root: Path,
    index_name: str,
    registry_path: Path,
    cache_root: Path,
    alias: str | None = None,
    portable_source: bool = False,
) -> None:
    published_skills_root = published_repo.path / "skills"
    _copy_skill_directories_to_repository(skills_root, published_skills_root)
    publish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(published_skills_root),
            "--index-name",
            index_name,
        ],
        cwd=published_repo.path,
    )
    publish_result.assert_success()
    published_repo.commit_all("Publish skill index")

    add_arguments = [
        "add-index",
        "--source",
        published_repo.path.as_uri() if portable_source else str(published_repo.path),
    ]
    if alias is not None:
        add_arguments.extend(["--alias", alias])
    add_arguments.extend(
        [
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )
    add_result = run_cli(add_arguments)
    add_result.assert_success()


def _copy_skill_directories_to_repository(skills_root: Path, repository: Path) -> None:
    for skill_directory in skills_root.iterdir():
        if skill_directory.is_dir():
            shutil.copytree(
                skill_directory,
                repository / skill_directory.name,
                dirs_exist_ok=True,
            )


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return cast("dict[str, Any]", json.load(file))


def _valid_skill_content(name: str, description: str) -> str:
    return f"""---
name: {name}
description: {description}
metadata:
  version: "1.0.0"
  dependencies:
    tools:
      - name: git
        purpose: Inspect version-control state.
        required: true
    skills: []
---
# {name}
"""


def _git_head(repository: Path) -> str:
    head = repository / ".git" / "refs" / "heads" / "master"
    return head.read_text(encoding="utf-8").strip()
