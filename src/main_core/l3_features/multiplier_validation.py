"""Shared validation for L3 feature weight multipliers."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from math import isfinite

from main_core.l3_features.errors import InvalidMultiplierError


def validate_multiplier_mapping(updates: Mapping[str, object]) -> dict[str, float]:
    """Return a float copy after enforcing positive finite multipliers."""

    invalid_keys = [
        str(feature_name)
        for feature_name, multiplier in updates.items()
        if not _is_valid_multiplier(multiplier)
    ]
    if invalid_keys:
        raise InvalidMultiplierError("feature weight multipliers must be finite and > 0")
    return {
        str(feature_name): float(multiplier)
        for feature_name, multiplier in updates.items()
    }


def _is_valid_multiplier(multiplier: object) -> bool:
    if isinstance(multiplier, bool):
        return False
    if isinstance(multiplier, int | float):
        return isfinite(multiplier) and multiplier > 0
    if isinstance(multiplier, Decimal):
        return multiplier.is_finite() and multiplier > 0
    return False


__all__ = ["validate_multiplier_mapping"]
