"""Shared validation for L3 feature weight multipliers."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from main_core.l3_features.errors import InvalidMultiplierError


def validate_multiplier_mapping(updates: Mapping[str, Any]) -> dict[str, float]:
    """Return a finite positive float copy of a multiplier mapping."""

    validated_updates: dict[str, float] = {}
    for feature_name, multiplier in updates.items():
        try:
            converted_multiplier = _convert_multiplier(multiplier)
        except (OverflowError, TypeError, ValueError) as exc:
            raise InvalidMultiplierError(
                "feature weight multipliers must be finite and > 0"
            ) from exc

        if not isfinite(converted_multiplier) or converted_multiplier <= 0:
            raise InvalidMultiplierError(
                "feature weight multipliers must be finite and > 0"
            )
        validated_updates[feature_name] = converted_multiplier
    return validated_updates


def _convert_multiplier(multiplier: Any) -> float:
    if isinstance(multiplier, bool):
        raise TypeError("bool is not a valid feature weight multiplier")
    return float(multiplier)


__all__ = ["validate_multiplier_mapping"]
