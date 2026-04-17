"""Tests for default L7 recommendation constraints."""

from __future__ import annotations

from main_core.common.contexts import RecommendationConstraintInputs
from main_core.common.schemas import RecommendationSnapshot, WorldStateSnapshot
from main_core.l7_recommendation import DefaultConstraintProvider


def _world_state(final_regime: str = "neutral") -> WorldStateSnapshot:
    if final_regime == "risk_off":
        baseline_regime = "neutral"
        llm_delta = -1
    else:
        baseline_regime = final_regime
        llm_delta = 0
    return WorldStateSnapshot(
        cycle_id="cycle_l7",
        baseline_regime=baseline_regime,
        llm_delta=llm_delta,
        final_regime=final_regime,
        llm_rationale="fixture",
        actual_model_used="fixture",
        actual_provider="local",
        fallback_path=[],
    )


def _candidate(action_type: str = "buy") -> RecommendationSnapshot:
    return RecommendationSnapshot(
        cycle_id="cycle_l7",
        entity_id="ENT_A",
        action_type=action_type,
        rating="A",
        confidence=0.8,
        triggered_by="system",
        override_applied=False,
        constraints_applied={"existing": "kept"},
    )


def test_default_constraint_provider_downgrades_buy_in_risk_off() -> None:
    provider = DefaultConstraintProvider()

    result = provider.gate(
        RecommendationConstraintInputs(world_state=_world_state("risk_off")),
        _candidate(),
    )

    assert result.action_type == "hold"
    assert result.rating == "B"
    assert result.constraints_applied == {
        "existing": "kept",
        "regime_gate": "risk_off_buy_to_hold",
    }


def test_default_constraint_provider_forces_inconclusive_from_risk_context() -> None:
    provider = DefaultConstraintProvider()

    result = provider.gate(
        RecommendationConstraintInputs(
            world_state=_world_state(),
            risk_context={"force_inconclusive": True},
        ),
        _candidate(),
    )

    assert result.action_type == "inconclusive"
    assert result.rating is None
    assert result.confidence is None
    assert result.constraints_applied["risk_gate"] == "force_inconclusive"
