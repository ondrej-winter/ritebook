from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from tests.e2e.conftest import run_git

if TYPE_CHECKING:
    from tests.e2e.conftest import (
        CliResult,
        CliRunner,
        GitRepository,
        GitRepositoryFactory,
        SkillWriter,
    )


@dataclass(frozen=True)
class InstalledContributionSkill:
    """Paths and repository state for one lockfile-backed installed skill."""

    source_repository: GitRepository
    consumer_repository: Path
    installed_skill: Path
    lockfile: Path
    contribution_root: Path


def test_publish_skill_change_creates_isolated_branch_and_commit(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    installed = _install_contribution_skill(
        tmp_path=tmp_path,
        run_cli=run_cli,
        skills_root=skills_root,
        write_valid_skill=write_valid_skill,
        git_repository=git_repository,
        registry_path=registry_path,
        cache_root=cache_root,
    )
    skill_file = installed.installed_skill / "SKILL.md"
    _replace_description(
        skill_file,
        replacement="Helps review code changes carefully.",
    )

    result = _publish_skill_change(run_cli, installed)

    result.assert_success()
    assert result.stderr == ""
    output = _prepared_output(result)
    assert output.skill_reference == "company-skills/code-review"
    assert re.fullmatch(r"ritebook/code-review-\d{14}", output.branch_name)
    assert re.fullmatch(r"[0-9a-f]{40}", output.commit_hash)
    assert output.checkout.is_relative_to(installed.contribution_root)
    assert output.checkout != installed.source_repository.path
    assert output.next_step == (
        "Next: inspect the checkout and push or share the branch manually; "
        "no usable origin remote is configured."
    )
    assert (
        _git_output(output.checkout, "branch", "--show-current") == output.branch_name
    )
    assert _git_output(output.checkout, "rev-parse", "HEAD") == output.commit_hash
    assert _git_output(output.checkout, "show", "-s", "--format=%s", "HEAD") == (
        "Update code-review skill from Ritebook contribution"
    )
    assert (output.checkout / "code-review" / "SKILL.md").read_text(
        encoding="utf-8",
    ) == skill_file.read_text(encoding="utf-8")
    generated_index = _read_json(output.checkout / "ritebook-index.json")
    assert generated_index["skills"][0]["description"] == (
        "Helps review code changes carefully."
    )
    _assert_source_repository_unchanged(installed.source_repository)


def test_publish_skill_change_reports_no_local_changes(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    installed = _install_contribution_skill(
        tmp_path=tmp_path,
        run_cli=run_cli,
        skills_root=skills_root,
        write_valid_skill=write_valid_skill,
        git_repository=git_repository,
        registry_path=registry_path,
        cache_root=cache_root,
    )

    result = _publish_skill_change(run_cli, installed)

    result.assert_success()
    assert result.stdout == (
        "No local changes to publish for company-skills/code-review\n"
    )
    assert result.stderr == ""
    checkout = _single_contribution_checkout(installed.contribution_root)
    assert _git_output(checkout, "branch", "--list", "ritebook/*") == ""
    assert _git_output(checkout, "rev-parse", "HEAD") == _git_output(
        installed.source_repository.path,
        "rev-parse",
        "HEAD",
    )
    _assert_source_repository_unchanged(installed.source_repository)


def test_publish_skill_change_fails_when_upstream_skill_changed(
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    installed = _install_contribution_skill(
        tmp_path=tmp_path,
        run_cli=run_cli,
        skills_root=skills_root,
        write_valid_skill=write_valid_skill,
        git_repository=git_repository,
        registry_path=registry_path,
        cache_root=cache_root,
    )
    _replace_description(
        installed.source_repository.path / "code-review" / "SKILL.md",
        replacement="Helps review upstream code changes.",
    )
    installed.source_repository.commit_all("Update skill upstream")

    result = _publish_skill_change(run_cli, installed)

    result.assert_failure()
    assert result.stdout == ""
    assert result.stderr == (
        "ritebook: error: upstream changed since locked revision; update or reinstall "
        "the skill or reconcile the source changes manually before retrying\n"
    )
    checkout = _single_contribution_checkout(installed.contribution_root)
    assert _git_output(checkout, "branch", "--list", "ritebook/*") == ""
    assert _git_output(checkout, "rev-parse", "HEAD") == _git_output(
        installed.source_repository.path,
        "rev-parse",
        "HEAD",
    )
    _assert_source_repository_unchanged(installed.source_repository)


@dataclass(frozen=True)
class PreparedOutput:
    """Parsed successful contribution output used for observable assertions."""

    skill_reference: str
    branch_name: str
    commit_hash: str
    checkout: Path
    next_step: str


def _install_contribution_skill(
    *,
    tmp_path: Path,
    run_cli: CliRunner,
    skills_root: Path,
    write_valid_skill: SkillWriter,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> InstalledContributionSkill:
    source_repository = git_repository(tmp_path / "published-index")
    write_valid_skill("code-review", "Helps review code changes.")

    publish_result = run_cli(
        [
            "publish-index",
            "--skills-root",
            str(skills_root),
            "--index-name",
            "company-skills",
        ],
        cwd=source_repository.path,
    )
    publish_result.assert_success()
    shutil.copytree(
        skills_root / "code-review",
        source_repository.path / "code-review",
    )
    source_repository.commit_all("Publish skill index")

    add_result = run_cli(
        [
            "add-index",
            "--source",
            str(source_repository.path),
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )
    add_result.assert_success()

    consumer = tmp_path / "consumer"
    requirements_file = consumer / "ritebook.toml"
    lockfile = consumer / "state" / "ritebook.lock"
    contribution_root = tmp_path / "contributions"
    consumer.mkdir()
    requirements_file.write_text(
        """
[targets]
agents = ".agents/skills"

[[skills]]
name = "company-skills/code-review"
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
        cwd=consumer,
    )
    install_result.assert_success()
    return InstalledContributionSkill(
        source_repository=source_repository,
        consumer_repository=consumer,
        installed_skill=consumer / ".agents" / "skills" / "code-review",
        lockfile=lockfile,
        contribution_root=contribution_root,
    )


def _publish_skill_change(
    run_cli: CliRunner,
    installed: InstalledContributionSkill,
) -> CliResult:
    return run_cli(
        [
            "publish-skill-change",
            "company-skills/code-review",
            "--lockfile",
            str(installed.lockfile),
            "--contribution-root",
            str(installed.contribution_root),
        ],
        cwd=installed.consumer_repository,
    )


def _prepared_output(result: CliResult) -> PreparedOutput:
    lines = result.stdout.splitlines()
    assert len(lines) == 5
    return PreparedOutput(
        skill_reference=lines[0].removeprefix("Prepared contribution for "),
        branch_name=lines[1].removeprefix("Branch: "),
        commit_hash=lines[2].removeprefix("Commit: "),
        checkout=Path(lines[3].removeprefix("Checkout: ")),
        next_step=lines[4],
    )


def _replace_description(skill_file: Path, *, replacement: str) -> None:
    content = skill_file.read_text(encoding="utf-8")
    skill_file.write_text(
        content.replace("Helps review code changes.", replacement),
        encoding="utf-8",
    )


def _single_contribution_checkout(contribution_root: Path) -> Path:
    markers = tuple(
        contribution_root.glob("*/*/.git/ritebook-contribution-workspace"),
    )
    assert len(markers) == 1
    return markers[0].parents[1]


def _git_output(repository: Path, *arguments: str) -> str:
    return run_git(repository, *arguments).stdout.strip()


def _assert_source_repository_unchanged(repository: GitRepository) -> None:
    assert _git_output(repository.path, "status", "--short") == ""


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return cast("dict[str, Any]", json.load(file))
