from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import grimp


def test_architecture_graph_covers_every_source_module() -> None:
    source_root = Path(__file__).resolve().parents[2] / "src"
    expected_modules = set()
    for source_file in (source_root / "ritebook").rglob("*.py"):
        parts = source_file.relative_to(source_root).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        expected_modules.add(".".join(parts))

    graph = grimp.build_graph("ritebook", cache_dir=None)

    assert expected_modules <= graph.modules, sorted(expected_modules - graph.modules)


def test_architecture_check_rejects_feature_core_adapter_import(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[2]
    shutil.copytree(repository / "src", tmp_path / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(repository / "pyproject.toml", tmp_path / "pyproject.toml")
    domain_file = tmp_path / "src/ritebook/features/publisher/domain/catalog.py"
    with domain_file.open("a", encoding="utf-8") as stream:
        stream.write("\nimport ritebook.adapters.inbound.cli.adapter\n")
    lint_imports = shutil.which("lint-imports")
    assert lint_imports is not None

    result = subprocess.run(  # noqa: S603 - run the installed architecture checker against an isolated source copy.
        [lint_imports, "--no-cache", "--no-logo"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path / "src")},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Feature cores do not import adapters BROKEN" in result.stdout
    assert "ritebook.features.publisher.domain.catalog" in result.stdout
