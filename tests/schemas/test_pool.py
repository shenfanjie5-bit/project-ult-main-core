"""Tests for OfficialAlphaPool."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from main_core.common.schemas import FormalObjectBase, OfficialAlphaPool

DEFAULT_OFFICIAL_ALPHA_POOL_CAPACITY = 100


def _pool() -> OfficialAlphaPool:
    return OfficialAlphaPool(
        cycle_id="cycle-20260417",
        observation_pool_size=250,
        official_alpha_pool_capacity=3,
        selected_entities=["ENT_001", "ENT_002"],
        added_entities=["ENT_002"],
        removed_entities=[],
        freeze_reason_map={"ENT_001": "existing core holding"},
    )


def test_pool_happy_path_default_capacity_and_round_trip() -> None:
    pool = _pool()
    default_capacity_pool = OfficialAlphaPool(
        cycle_id="cycle-20260417",
        observation_pool_size=250,
        selected_entities=["ENT_001"],
        added_entities=[],
        removed_entities=[],
        freeze_reason_map={},
    )

    assert isinstance(pool, FormalObjectBase)
    assert (
        default_capacity_pool.official_alpha_pool_capacity
        == DEFAULT_OFFICIAL_ALPHA_POOL_CAPACITY
    )
    assert OfficialAlphaPool.from_json(pool.to_json()) == pool


def test_pool_rejects_missing_required_field() -> None:
    payload = _pool().model_dump()
    payload.pop("selected_entities")

    with pytest.raises(ValidationError):
        OfficialAlphaPool(**payload)


def test_pool_rejects_non_positive_capacity() -> None:
    payload = _pool().model_dump()
    payload["official_alpha_pool_capacity"] = 0

    with pytest.raises(ValidationError):
        OfficialAlphaPool(**payload)


def test_pool_rejects_selected_entities_over_capacity() -> None:
    with pytest.raises(ValidationError):
        OfficialAlphaPool(
            cycle_id="cycle-20260417",
            observation_pool_size=101,
            official_alpha_pool_capacity=100,
            selected_entities=[f"ENT_{index:03d}" for index in range(101)],
            added_entities=[],
            removed_entities=[],
            freeze_reason_map={},
        )
