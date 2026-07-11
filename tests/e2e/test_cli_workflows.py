from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path

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
    write_valid_skill("beta", "Helps with beta workflows.")

    lint_result = run_cli(["lint-skills", "--skills-root", str(skills_root)])
    lint_result.assert_success()
    assert lint_result.stdout == "Validated 2 skill(s)\n"

    publish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(skills_root),
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
        "    └── beta — Helps with beta workflows.\n"
    )

    write_valid_skill("gamma", "Helps with gamma workflows.")
    republish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(skills_root),
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
        "    ├── beta — Helps with beta workflows.\n"
        "    └── gamma — Helps with gamma workflows.\n"
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
            "index_schema_version": 1,
            "skill_path": "code-review",
            "skill_file": "code-review/SKILL.md",
            "installed_at": installation_registry["installations"][0]["installed_at"],
        },
    ]


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
        "source": str(published_repo.path),
        "source_type": "local_git_repo",
        "index_schema_version": 1,
        "skill_path": "code-review",
        "skill_file": "code-review/SKILL.md",
        "locked_at": lockfile_data["skills"][0]["locked_at"],
        "target_ref": "claude",
        "source_revision": _git_head(published_repo.path),
    }
    assert lockfile_data["skills"][1]["target"] == ".agents/skills/tdd"
    assert "target_ref" not in lockfile_data["skills"][1]


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
) -> None:
    publish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(skills_root),
            "--index-name",
            index_name,
        ],
        cwd=published_repo.path,
    )
    publish_result.assert_success()
    _copy_skill_directories_to_repository(skills_root, published_repo.path)
    published_repo.commit_all("Publish skill index")

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


def _git_head(repository: Path) -> str:
    head = repository / ".git" / "refs" / "heads" / "master"
    return head.read_text(encoding="utf-8").strip()
