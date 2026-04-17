"""Tests for RecommendationSnapshot."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from main_core.common.schemas import FormalObjectBase, RecommendationSnapshot


def _recommendation() -> RecommendationSnapshot:
    return RecommendationSnapshot(
        cycle_id="cycle-20260417",
        entity_id="ENT_001",
        action_type="buy",
        rating="A",
        confidence=0.72,
        triggered_by="system",
        override_applied=False,
        constraints_applied={"regime": "risk_on"},
    )


def test_recommendation_happy_path_and_round_trip() -> None:
    recommendation = _recommendation()

    assert isinstance(recommendation, FormalObjectBase)
    assert RecommendationSnapshot.from_json(recommendation.to_json()) == recommendation


def test_recommendation_rejects_missing_required_field() -> None:
    payload = _recommendation().model_dump()
    payload.pop("triggered_by")

    with pytest.raises(ValidationError):
        RecommendationSnapshot(**payload)


def test_recommendation_rejects_unknown_action_type() -> None:
    payload = _recommendation().model_dump()
    payload["action_type"] = "sell"

    with pytest.raises(ValidationError):
        RecommendationSnapshot(**payload)


def test_recommendation_rejects_inconclusive_with_confidence() -> None:
    payload = _recommendation().model_dump()
    payload["action_type"] = "inconclusive"
    payload["confidence"] = 0.2

    with pytest.raises(ValidationError):
        RecommendationSnapshot(**payload)


def test_recommendation_accepts_inconclusive_without_confidence() -> None:
    recommendation = RecommendationSnapshot(
        cycle_id="cycle-20260417",
        entity_id="ENT_001",
        action_type="inconclusive",
        rating=None,
        confidence=None,
        triggered_by="system",
        override_applied=False,
        constraints_applied={"reason": "alpha inconclusive"},
    )

    assert recommendation.confidence is None
