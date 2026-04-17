"""Tests for AlphaResultSnapshot."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from main_core.common.schemas import AlphaResultSnapshot, FormalObjectBase, single_prompt_result


def _alpha_result() -> AlphaResultSnapshot:
    return AlphaResultSnapshot(
        cycle_id="cycle-20260417",
        entity_id="ENT_001",
        analyzer_type="single_prompt_v1",
        score=0.82,
        confidence=0.76,
        rationale="Earnings revision and price action align.",
        similar_cases=[{"entity_id": "ENT_099", "score": 0.8}],
        status="ok",
    )


def test_alpha_result_happy_path_and_round_trip() -> None:
    result = _alpha_result()

    assert isinstance(result, FormalObjectBase)
    assert AlphaResultSnapshot.from_json(result.to_json()) == result


def test_single_prompt_result_factory_uses_p2_default_analyzer() -> None:
    result = single_prompt_result(
        cycle_id="cycle-20260417",
        entity_id="ENT_001",
        score=0.9,
        confidence=0.8,
        rationale="Factory output.",
        similar_cases=[],
    )

    assert result.analyzer_type == "single_prompt_v1"


def test_alpha_result_rejects_missing_required_field() -> None:
    payload = _alpha_result().model_dump()
    payload.pop("rationale")

    with pytest.raises(ValidationError):
        AlphaResultSnapshot(**payload)


def test_alpha_result_rejects_unknown_analyzer_type() -> None:
    payload = _alpha_result().model_dump()
    payload["analyzer_type"] = "gpt5_v2"

    with pytest.raises(ValidationError):
        AlphaResultSnapshot(**payload)


def test_alpha_result_rejects_inconclusive_with_score() -> None:
    payload = _alpha_result().model_dump()
    payload["status"] = "inconclusive"
    payload["score"] = 0.5

    with pytest.raises(ValidationError):
        AlphaResultSnapshot(**payload)


def test_alpha_result_accepts_inconclusive_without_score() -> None:
    result = single_prompt_result(
        cycle_id="cycle-20260417",
        entity_id="ENT_001",
        score=None,
        confidence=0.0,
        rationale="Provider timeout.",
        similar_cases=[],
        status="inconclusive",
    )

    assert result.score is None
    assert result.status == "inconclusive"
