from pathlib import PurePosixPath

import pytest

from ritebook.shared_kernel.portable_paths import (
    PortablePathValidationError,
    validate_portable_relative_posix_path,
)


@pytest.mark.parametrize("value", ["skills", "skills/code-review", "skills/équipe"])
def test_validate_portable_relative_posix_path_accepts_literal_paths(
    value: str,
) -> None:
    assert validate_portable_relative_posix_path(
        value,
        field_name="skills_root",
    ) == PurePosixPath(value)


def test_validate_portable_relative_posix_path_allows_explicit_current_directory() -> None:
    assert validate_portable_relative_posix_path(
        ".",
        field_name="skills_root",
        allow_current_directory=True,
    ) == PurePosixPath(".")


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "./skills",
        "skills/.",
        "../skills",
        "skills/../other",
        "/skills",
        "skills/",
        "skills//code-review",
        "skills\\code-review",
    ],
)
def test_validate_portable_relative_posix_path_rejects_non_literal_paths(
    value: str,
) -> None:
    with pytest.raises(PortablePathValidationError):
        validate_portable_relative_posix_path(value, field_name="skills_root")


@pytest.mark.parametrize(
    "value",
    [
        "skills/name.",
        "skills/name ",
        "skills/name:variant",
        "skills/name*variant",
        "skills/CON",
        "skills/con.txt",
        "skills/COM1",
        "skills/lpt9.json",
        "skills/line\nbreak",
        "skills/\ud800",
    ],
)
def test_validate_portable_relative_posix_path_rejects_non_portable_segments(
    value: str,
) -> None:
    with pytest.raises(PortablePathValidationError):
        validate_portable_relative_posix_path(value, field_name="skills_root")
