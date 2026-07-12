"""Application errors for skill linting workflows."""


class LinterError(Exception):
    """Base application error for skill linting workflows."""


class LintSkillsDiscoveryError(LinterError):
    """Raised when skill headers cannot be discovered for linting."""
