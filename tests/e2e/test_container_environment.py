from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from shutil import which


def test_docker_runner_uses_clean_installed_wheel_environment() -> None:
    assert os.geteuid() != 0
    assert os.environ["RITEBOOK_DOCKER_E2E"] == "1"

    home = Path(os.environ["HOME"])
    assert Path.home() == home
    assert home.is_dir()
    assert os.access(home, os.W_OK)

    for variable in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
        controlled_path = Path(os.environ[variable])
        assert controlled_path.is_relative_to(home)
        assert controlled_path.is_dir()
        assert os.access(controlled_path, os.W_OK)

    test_venv = Path(os.environ["RITEBOOK_E2E_TEST_VENV"])
    consumer_venv = Path(os.environ["RITEBOOK_E2E_CONSUMER_VENV"])
    assert Path(sys.prefix) == test_venv
    assert importlib.util.find_spec("ritebook") is None

    ritebook = which("ritebook")
    assert ritebook is not None
    ritebook_executable = Path(ritebook)
    assert ritebook_executable == consumer_venv / "bin" / "ritebook"
    assert ritebook_executable.read_text(encoding="utf-8").splitlines()[0] == (f"#!{consumer_venv}/bin/python")

    import_probe = """
import pathlib
import ritebook

print(pathlib.Path(ritebook.__file__).resolve())
"""
    completed = subprocess.run(  # noqa: S603 - fixed consumer environment executable.
        (
            str(consumer_venv / "bin" / "python"),
            "-c",
            import_probe,
        ),
        check=True,
        capture_output=True,
        text=True,
    )
    installed_module = Path(completed.stdout.strip())
    assert installed_module.is_relative_to(consumer_venv)

    workspace = Path.cwd()
    assert not (workspace / "src").exists()
    assert not (workspace / "pyproject.toml").exists()
    assert not (workspace / "uv.lock").exists()
