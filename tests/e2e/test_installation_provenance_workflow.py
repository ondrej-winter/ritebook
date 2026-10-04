from __future__ import annotations

import json
import shutil
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


def test_install_skill_uses_registered_commit_after_source_head_advances(
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

    write_valid_skill("code-review", "Helps review code changes.")
    published_guide = skills_root / "code-review" / "guide.md"
    published_guide.write_text("validated content\n", encoding="utf-8")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        registry_path=registry_path,
        cache_root=cache_root,
    )
    registered_revision = _read_json(registry_path)["indexes"][0]["source_revision"]

    source_guide = published_repo.path / "skills" / "code-review" / "guide.md"
    source_guide.write_text("unvalidated newer content\n", encoding="utf-8")
    published_repo.commit_all("Advance source without updating registered index")
    assert _git_head(published_repo.path) != registered_revision

    result = _install_skill(
        run_cli=run_cli,
        target=target,
        registry_path=registry_path,
        installation_registry_path=installation_registry_path,
    )

    result.assert_success()
    assert (target / "guide.md").read_text(encoding="utf-8") == "validated content\n"
    installation = _read_json(installation_registry_path)["installations"][0]
    assert installation["source_revision"] == registered_revision


def test_install_skill_rejects_cached_index_digest_mismatch_before_copy(
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

    write_valid_skill("code-review", "Helps review code changes.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        registry_path=registry_path,
        cache_root=cache_root,
    )
    registered_index = _read_json(registry_path)["indexes"][0]
    Path(registered_index["cached_index_path"]).write_text(
        '{"schema_version": 1, "skills": []}\n',
        encoding="utf-8",
    )

    result = _install_skill(
        run_cli=run_cli,
        target=target,
        registry_path=registry_path,
        installation_registry_path=installation_registry_path,
    )

    result.assert_failure()
    assert result.stdout == ""
    assert result.stderr == (
        "ritebook: error: cached index digest mismatch; "
        "run update-index to regenerate it\n"
    )
    assert not target.exists()
    assert not installation_registry_path.exists()


def test_install_skill_rejects_bound_commit_index_mismatch_before_copy(
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

    write_valid_skill("code-review", "Helps review code changes.")
    _publish_and_register_index(
        run_cli=run_cli,
        published_repo=published_repo,
        skills_root=skills_root,
        registry_path=registry_path,
        cache_root=cache_root,
    )
    index_path = published_repo.path / "ritebook-index.json"
    changed_index = _read_json(index_path)
    changed_index["generated_at"] = "2026-10-04T00:00:00Z"
    index_path.write_text(f"{json.dumps(changed_index, indent=2)}\n", encoding="utf-8")
    published_repo.commit_all("Commit a different index binding")

    registry = _read_json(registry_path)
    registry["indexes"][0]["source_revision"] = _git_head(published_repo.path)
    registry_path.write_text(f"{json.dumps(registry, indent=2)}\n", encoding="utf-8")

    result = _install_skill(
        run_cli=run_cli,
        target=target,
        registry_path=registry_path,
        installation_registry_path=installation_registry_path,
    )

    result.assert_failure()
    assert result.stdout == ""
    assert result.stderr == (
        "ritebook: error: bound commit index mismatch; "
        "run update-index to revalidate the source\n"
    )
    assert not target.exists()
    assert not installation_registry_path.exists()


def _publish_and_register_index(
    *,
    run_cli: CliRunner,
    published_repo: GitRepository,
    skills_root: Path,
    registry_path: Path,
    cache_root: Path,
) -> None:
    published_skills_root = published_repo.path / "skills"
    shutil.copytree(skills_root, published_skills_root)
    publish_result = run_cli(
        [
            "indexes",
            "publish",
            "--skills-root",
            str(published_skills_root),
            "--name",
            "company-skills",
        ],
        cwd=published_repo.path,
    )
    publish_result.assert_success()
    published_repo.commit_all("Publish skill index")

    add_result = run_cli(
        [
            "indexes",
            "add",
            "--source",
            str(published_repo.path),
            "--registry-path",
            str(registry_path),
            "--cache-root",
            str(cache_root),
        ],
    )
    add_result.assert_success()


def _install_skill(
    *,
    run_cli: CliRunner,
    target: Path,
    registry_path: Path,
    installation_registry_path: Path,
) -> CliResult:
    return run_cli(
        [
            "skills",
            "install",
            "company-skills/code-review",
            "--target",
            str(target),
            "--registry-path",
            str(registry_path),
            "--installation-registry-path",
            str(installation_registry_path),
        ],
    )


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return cast("dict[str, Any]", json.load(file))


def _git_head(repository: Path) -> str:
    return run_git(repository, "rev-parse", "HEAD").stdout.strip()
