"""Tests for L3 multiplier storage."""

from __future__ import annotations

import pytest

from main_core.common.types import CycleId
from main_core.l3_features import InMemoryMultiplierStore, InvalidMultiplierError


def test_in_memory_multiplier_store_is_cycle_scoped() -> None:
    store = InMemoryMultiplierStore()

    store.put_multipliers(CycleId("cycle-001"), {"close_price": 1.2})

    assert store.get_multipliers("cycle-001") == {"close_price": 1.2}
    assert store.get_multipliers("cycle-002") == {}


def test_in_memory_multiplier_store_returns_defensive_copy() -> None:
    store = InMemoryMultiplierStore()
    store.put_multipliers("cycle-001", {"close_price": 1.2})

    returned_multipliers = store.get_multipliers("cycle-001")
    returned_multipliers["close_price"] = 9.9

    assert store.get_multipliers("cycle-001") == {"close_price": 1.2}


def test_in_memory_multiplier_store_defensively_copies_updates() -> None:
    store = InMemoryMultiplierStore()
    updates = {"close_price": 1.2}

    store.put_multipliers("cycle-001", updates)
    updates["close_price"] = 9.9

    assert store.get_multipliers("cycle-001") == {"close_price": 1.2}


@pytest.mark.parametrize("invalid_multiplier", [0.0, -0.1, float("nan"), float("inf")])
def test_in_memory_multiplier_store_rejects_invalid_values(
    invalid_multiplier: float,
) -> None:
    store = InMemoryMultiplierStore()

    with pytest.raises(InvalidMultiplierError, match="finite and > 0"):
        store.put_multipliers("cycle-001", {"close_price": invalid_multiplier})

    assert store.get_multipliers("cycle-001") == {}
