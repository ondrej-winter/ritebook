from importlib.metadata import version

from ritebook import __version__


def test_package_exposes_version() -> None:
    assert __version__ == version("ritebook")
