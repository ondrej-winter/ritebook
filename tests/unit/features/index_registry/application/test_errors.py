from ritebook.features.index_registry.application.errors import (
    DuplicateIndexNameError,
    UnknownIndexNameError,
)


def test_duplicate_index_name_error_mentions_force() -> None:
    assert str(DuplicateIndexNameError("company-skills")) == (
        "index company-skills already exists; use --force to replace it"
    )


def test_unknown_index_name_error_is_user_facing() -> None:
    assert str(UnknownIndexNameError("company-skills")) == (
        "index company-skills is not registered"
    )
