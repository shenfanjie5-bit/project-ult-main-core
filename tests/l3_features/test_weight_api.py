"""Tests for the public L3 multiplier API."""

from __future__ import annotations

import pytest

from main_core.l3_features import (
    InMemoryMultiplierStore,
    InvalidMultiplierError,
    apply_weight_multiplier,
    get_feature_weight_multiplier,
)


class FalseyMultiplierStore(InMemoryMultiplierStore):
    def __len__(self) -> int:
        return 0


class InvalidReadMultiplierStore:
    def get_multipliers(self, cycle_id: str) -> dict[str, float]:
        return {"close_price": -1.0}

    def put_multipliers(self, cycle_id: str, updates: dict[str, float]) -> None:
        raise AssertionError("get API must not write multipliers")


def test_weight_api_applies_updates_to_injected_store() -> None:
    store = InMemoryMultiplierStore()

    apply_weight_multiplier("cycle-001", {"close_price": 1.2}, store=store)
    apply_weight_multiplier("cycle-001", {"volume": 0.8}, store=store)

    assert get_feature_weight_multiplier("cycle-001", store=store) == {
        "close_price": 1.2,
        "volume": 0.8,
    }


def test_weight_api_returns_defensive_copy() -> None:
    store = InMemoryMultiplierStore()
    apply_weight_multiplier("cycle-001", {"close_price": 1.2}, store=store)

    returned_multipliers = get_feature_weight_multiplier("cycle-001", store=store)
    returned_multipliers["close_price"] = 9.9

    assert get_feature_weight_multiplier("cycle-001", store=store) == {"close_price": 1.2}


def test_weight_api_honors_falsey_custom_store() -> None:
    store = FalseyMultiplierStore()

    apply_weight_multiplier("cycle-001", {"close_price": 1.2}, store=store)

    assert get_feature_weight_multiplier("cycle-001", store=store) == {"close_price": 1.2}


def test_weight_api_validates_custom_store_read_path() -> None:
    with pytest.raises(InvalidMultiplierError, match="finite and > 0"):
        get_feature_weight_multiplier("cycle-001", store=InvalidReadMultiplierStore())
