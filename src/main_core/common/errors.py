"""Shared exception types for main-core."""


class MainCoreError(Exception):
    """Base exception for main-core failures."""


class InconclusiveError(MainCoreError):
    """Raised when a task must be marked inconclusive."""


class ManifestPublishError(MainCoreError):
    """Raised when manifest-backed publication fails."""


class BoundaryViolationError(MainCoreError):
    """Raised when a package boundary rule is violated."""


__all__ = [
    "BoundaryViolationError",
    "InconclusiveError",
    "MainCoreError",
    "ManifestPublishError",
]
