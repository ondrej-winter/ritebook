"""Pure validation for canonical Git branch references."""

from __future__ import annotations

_CANONICAL_BRANCH_PREFIX = "refs/heads/"
_ASCII_CONTROL_CHARACTER_LIMIT = 32


def require_canonical_git_branch(value: str, *, field_name: str) -> str:
    """Return a canonical full branch ref or raise ``ValueError``."""
    if not value.startswith(_CANONICAL_BRANCH_PREFIX):
        msg = f"{field_name} must be a canonical Git branch under refs/heads/."
        raise ValueError(msg)
    branch = value.removeprefix(_CANONICAL_BRANCH_PREFIX)
    invalid_characters = frozenset(" ~^:?*[\\")
    if (
        not branch
        or branch.startswith("/")
        or branch.endswith(("/", "."))
        or "//" in branch
        or ".." in branch
        or "@{" in branch
        or any(
            character in invalid_characters or ord(character) < _ASCII_CONTROL_CHARACTER_LIMIT for character in branch
        )
        or any(part.endswith(".lock") for part in branch.split("/"))
    ):
        msg = f"{field_name} must be a canonical Git branch under refs/heads/."
        raise ValueError(msg)
    return value
