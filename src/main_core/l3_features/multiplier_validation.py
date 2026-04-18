"""Shared validation for L3 feature weight multipliers."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from math import isfinite

from main_core.l3_features.errors import InvalidMultiplierError


def validate_multiplier_mapping(updates: Mapping[str, object]) -> dict[str, float]:
    """Return a float copy after enforcing positive finite multipliers."""

    validated_updates: dict[str, float] = {}
    invalid_keys: list[str] = []
    for feature_name, multiplier in updates.items():
        converted_multiplier = _validated_multiplier(multiplier)
        if converted_multiplier is None:
            invalid_keys.append(str(feature_name))
            continue
        validated_updates[str(feature_name)] = converted_multiplier
    if invalid_keys:
        raise InvalidMultiplierError("feature weight multipliers must be finite and > 0")
    return validated_updates


def _validated_multiplier(multiplier: object) -> float | None:
    if isinstance(multiplier, bool):
        return None
    if isinstance(multiplier, int | float | Decimal):
        try:
            converted_multiplier = float(multiplier)
        except (OverflowError, ValueError):
            return None
        if isfinite(converted_multiplier) and converted_multiplier > 0:
            return converted_multiplier
        return None
    return None


__all__ = ["validate_multiplier_mapping"]
