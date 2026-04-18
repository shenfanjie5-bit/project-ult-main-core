"""Public API for online feature weight multiplier updates."""

from __future__ import annotations

from collections.abc import Mapping

from main_core.common.types import CycleId
from main_core.l3_features.multiplier_store import (
    InMemoryMultiplierStore,
    MultiplierStore,
    validate_multiplier_mapping,
)

_DEFAULT_MULTIPLIER_STORE = InMemoryMultiplierStore()


def apply_weight_multiplier(
    cycle_id: CycleId | str,
    updates: Mapping[str, float],
    *,
    store: MultiplierStore | None = None,
) -> None:
    """Apply feature weight multiplier updates for a cycle."""

    validated_updates = validate_multiplier_mapping(updates)
    _resolve_store(store).put_multipliers(cycle_id, validated_updates)


def get_feature_weight_multiplier(
    cycle_id: CycleId | str,
    *,
    store: MultiplierStore | None = None,
) -> dict[str, float]:
    """Return the currently visible feature weight multipliers for a cycle."""

    return validate_multiplier_mapping(_resolve_store(store).get_multipliers(cycle_id))


def _resolve_store(store: MultiplierStore | None) -> MultiplierStore:
    return store if store is not None else _DEFAULT_MULTIPLIER_STORE


__all__ = ["apply_weight_multiplier", "get_feature_weight_multiplier"]
