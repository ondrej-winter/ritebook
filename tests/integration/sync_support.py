"""Isolated local-Git project fixtures for source-CLI sync workflows."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tests.integration.conftest import valid_skill_content

if TYPE_CHECKING:
    from tests.integration.conftest import GitRepository, GitRepositoryFactory

HELPER = Path(__file__).with_name("sync_process_helper.py")
REFERENCE = "company-skills/code-review"


@dataclass
class SyncProject:
    consumer: Path
    upstream: GitRepository
    environment: dict[str, str]
    registry: Path

    @property
    def requirements(self) -> Path:
        return self.consumer / "ritebook.toml"

    @property
    def lockfile(self) -> Path:
        return self.consumer / "state" / "custom.lock"

    @property
    def target(self) -> Path:
        return self.consumer / "skills" / "code-review"

    def cli(self, *arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - isolated local source CLI.
            [sys.executable, str(HELPER), *arguments],
            cwd=cwd or self.consumer,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )

    def sync_arguments(self, *, force: bool = False) -> list[str]:
        arguments = [
            "skills",
            "sync",
            "--file",
            str(self.requirements),
            "--lockfile",
            str(self.lockfile),
            "--registry-path",
            str(self.registry),
        ]
        return [*arguments, "--force"] if force else arguments

    def sync(self, *, force: bool = False) -> subprocess.CompletedProcess[str]:
        return self.cli(*self.sync_arguments(force=force))

    def advance_source(self, content: str) -> None:
        (self.upstream.path / "skills" / "code-review" / "guide.md").write_text(content)
        self.upstream.commit_all("Advance verified skill content")


def create_sync_project(tmp_path: Path, git_repository: GitRepositoryFactory) -> SyncProject:
    home = tmp_path / "home"
    home.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / "config"),
            "XDG_CACHE_HOME": str(home / "cache"),
            "PYTHONPATH": str(Path(__file__).parents[2] / "src"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "user.name",
            "GIT_CONFIG_VALUE_0": "Ritebook Integration",
            "GIT_CONFIG_KEY_1": "user.email",
            "GIT_CONFIG_VALUE_1": "ritebook-integration@example.invalid",
        }
    )
    upstream = git_repository(tmp_path / "upstream")
    skill = upstream.path / "skills" / "code-review"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(valid_skill_content("code-review", "Helps review changes."))
    (skill / "guide.md").write_text("original verified guide\n")
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    project = SyncProject(consumer, upstream, environment, home / "config" / "indexes.json")
    project.requirements.write_text(
        '[targets]\nagents = "skills"\n[[skills]]\nname = "company-skills/code-review"\ntarget = "agents"\n'
    )
    published = project.cli(
        "indexes", "publish", "--skills-root", "skills", "--name", "company-skills", cwd=upstream.path
    )
    assert published.returncode == 0, published.stderr
    upstream.commit_all("Publish verified skill index")
    registered = project.cli(
        "indexes", "add", "--source", upstream.path.as_uri(), "--registry-path", str(project.registry)
    )
    assert registered.returncode == 0, registered.stderr
    return project
