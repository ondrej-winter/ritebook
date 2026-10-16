from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.e2e.conftest import CliRunner, GitRepositoryFactory


def test_force_update_all_rebuilds_legacy_registry_from_saved_url(
    tmp_path: Path,
    run_cli: CliRunner,
    git_repository: GitRepositoryFactory,
    registry_path: Path,
    cache_root: Path,
) -> None:
    repository = git_repository(tmp_path / "upstream")
    content = json.dumps(
        {
            "schema_version": 1,
            "index": {"name": "published-skills"},
            "generated_at": "2026-10-16T00:00:00Z",
            "skills_root": ".",
            "skills": [],
        }
    ).encode()
    (repository.path / "ritebook-index.json").write_bytes(content)
    repository.commit_all("Publish index")
    registry_path.parent.mkdir(parents=True)
    original = json.dumps(
        {
            "schema_version": 1,
            "indexes": [
                {
                    "name": "local-alias",
                    "source": repository.path.as_uri(),
                    "source_type": "git_url",
                    "cached_index_path": str(tmp_path / "missing-cache"),
                }
            ],
        }
    ).encode()
    registry_path.write_bytes(original)
    arguments = ["indexes", "update", "--all", "--registry-path", str(registry_path), "--cache-root", str(cache_root)]

    ordinary = run_cli(arguments)
    ordinary.assert_failure()
    assert "indexes update --all --force" in ordinary.stderr
    assert registry_path.read_bytes() == original

    recovered = run_cli([*arguments, "--force"])
    recovered.assert_success()
    assert recovered.stdout == "Updated 1 index(es) with 0 total skill(s)\n"
    payload = json.loads(registry_path.read_bytes())
    assert payload["schema_version"] == 2
    entry = payload["indexes"][0]
    assert entry["name"] == "local-alias"
    assert entry["published_name"] == "published-skills"
    assert entry["source_branch"].startswith("refs/heads/")
    assert entry["index_digest"] == f"sha256:{hashlib.sha256(content).hexdigest()}"
    assert Path(entry["cached_index_path"]).read_bytes() == content
    listed = run_cli(["indexes", "list", "--registry-path", str(registry_path)])
    listed.assert_success()
    assert "local-alias" in listed.stdout
