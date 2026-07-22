# Ritebook project tooling override

This project-specific module intentionally overrides the reusable type-checking
defaults in `000-readme.md` and `011-tooling-and-ci.md`.

## Type checker

- **Must** use `ty` as Ritebook's only required static type checker.
- **Must** run `uv run ty check src/ritebook` for local validation and CI.
- **Must** keep the checked source scope aligned across `pyproject.toml`, pre-commit,
  CI, README, and specifications.
- **Must not** require `mypy` in addition to `ty` unless a future documented
  decision defines distinct ownership and failure policy for both checkers.

All other tooling and CI requirements in `011-tooling-and-ci.md` remain active.
