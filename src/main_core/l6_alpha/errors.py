"""Shared L6 analyzer exception types."""

from __future__ import annotations

from main_core.common.errors import MainCoreError


class AlphaAnalyzerError(MainCoreError):
    """Raised when the L6 analyzer contract is violated before provider work."""


class AlphaReasonerError(MainCoreError):
    """Raised when the L6 reasoner provider returns unusable infrastructure output."""


__all__ = ["AlphaAnalyzerError", "AlphaReasonerError"]
