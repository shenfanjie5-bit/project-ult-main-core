"""Tests for WorldStateSnapshot."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from main_core.common.schemas import FormalObjectBase, WorldStateSnapshot


def _world_state() -> WorldStateSnapshot:
    return WorldStateSnapshot(
        cycle_id="cycle-20260417",
        baseline_regime="neutral",
        llm_delta=1,
        final_regime="risk_on",
        llm_rationale="Market breadth improved.",
        actual_model_used="single-prompt-model",
        actual_provider="reasoner-runtime",
        fallback_path=[],
    )


def test_world_state_happy_path_and_round_trip() -> None:
    snapshot = _world_state()

    assert isinstance(snapshot, FormalObjectBase)
    assert WorldStateSnapshot.from_json(snapshot.to_json()) == snapshot


def test_world_state_rejects_missing_required_field() -> None:
    payload = _world_state().model_dump()
    payload.pop("actual_provider")

    with pytest.raises(ValidationError):
        WorldStateSnapshot(**payload)


def test_world_state_rejects_llm_delta_outside_contract() -> None:
    payload = _world_state().model_dump()
    payload["llm_delta"] = 2

    with pytest.raises(ValidationError):
        WorldStateSnapshot(**payload)


def test_world_state_rejects_impossible_final_regime_composition() -> None:
    payload = _world_state().model_dump()
    payload["final_regime"] = "risk_off"

    with pytest.raises(ValidationError):
        WorldStateSnapshot(**payload)


def test_world_state_rejects_regime_sequence_overflow() -> None:
    payload = _world_state().model_dump()
    payload["baseline_regime"] = "risk_on"
    payload["llm_delta"] = 1
    payload["final_regime"] = "risk_on"

    with pytest.raises(ValidationError):
        WorldStateSnapshot(**payload)
