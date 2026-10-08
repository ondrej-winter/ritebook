import pytest

from ritebook.shared_kernel.text_safety import (
    normalize_portable_description,
    require_portable_text,
)


def test_normalize_portable_description_trims_ordinary_unicode_text() -> None:
    assert (
        normalize_portable_description(
            "  Décrit quand utiliser la compétence.  ",
            field_name="Description",
        )
        == "Décrit quand utiliser la compétence."
    )


def test_normalize_portable_description_applies_length_after_trimming() -> None:
    assert (
        normalize_portable_description(
            f" {'x' * 1024} ",
            field_name="Description",
        )
        == "x" * 1024
    )


@pytest.mark.parametrize("value", ["", "   "])
def test_normalize_portable_description_rejects_blank_text(value: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        normalize_portable_description(value, field_name="Description")


def test_normalize_portable_description_rejects_over_limit_text() -> None:
    with pytest.raises(ValueError, match="at most 1024"):
        normalize_portable_description("x" * 1025, field_name="Description")


@pytest.mark.parametrize("value", ["line\nbreak", "delete\x7f", "c1\x80", "\ud800"])
def test_require_portable_text_rejects_controls_and_surrogates(value: str) -> None:
    with pytest.raises(ValueError, match="portable Unicode scalar text"):
        require_portable_text(value, field_name="Description")
