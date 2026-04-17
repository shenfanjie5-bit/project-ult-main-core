"""Tests for the L5 official alpha pool schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from main_core.common.schemas import OfficialAlphaPool


def _pool_payload() -> dict[str, object]:
    return {
        "cycle_id": "cycle_001",
        "observation_pool_size": 12,
        "official_alpha_pool_capacity": 2,
        "selected_entities": ["ENT_001", "ENT_002"],
        "added_entities": ["ENT_002"],
        "removed_entities": [],
        "freeze_reason_map": {"ENT_001": "existing core holding"},
    }


def test_official_alpha_pool_happy_path_round_trips_json() -> None:
    pool = OfficialAlphaPool(**_pool_payload())

    assert OfficialAlphaPool.from_json(pool.to_json()) == pool


def test_official_alpha_pool_missing_field_fails() -> None:
    payload = _pool_payload()
    payload.pop("selected_entities")

    with pytest.raises(ValidationError):
        OfficialAlphaPool(**payload)


def test_official_alpha_pool_rejects_selected_entities_over_capacity() -> None:
    payload = _pool_payload()
    payload["official_alpha_pool_capacity"] = 1

    with pytest.raises(ValidationError, match="selected_entities length"):
        OfficialAlphaPool(**payload)


@pytest.mark.parametrize(
    "capacity",
    [0, 101],
)
def test_official_alpha_pool_rejects_capacity_outside_hard_bounds(capacity: int) -> None:
    payload = _pool_payload()
    payload["official_alpha_pool_capacity"] = capacity

    with pytest.raises(ValidationError):
        OfficialAlphaPool(**payload)
