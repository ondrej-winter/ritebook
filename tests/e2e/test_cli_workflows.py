from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from tests.e2e.conftest import (
        CliRunner,
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
    assert result.stderr == (
        "missing-description/SKILL.md: description is required.\n"
    )
