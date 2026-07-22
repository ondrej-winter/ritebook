from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.skipif(
    os.environ.get("RITEBOOK_DOCKER_E2E") != "1",
    reason="container isolation assertions run only in the Docker E2E image",
)
def test_docker_runner_uses_isolated_unprivileged_environment() -> None:
    assert os.geteuid() != 0

    expected_directories = {
        "HOME": Path("/home/ritebook"),
        "XDG_CACHE_HOME": Path("/home/ritebook/.cache"),
        "XDG_CONFIG_HOME": Path("/home/ritebook/.config"),
    }
    for variable, expected_path in expected_directories.items():
        assert os.environ[variable] == str(expected_path)
        assert expected_path.is_dir()
        assert os.access(expected_path, os.W_OK)

    ipv4_routes = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()
    assert len(ipv4_routes) == 1
