"""Formal world state snapshot schema."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId, Regime

_REGIME_SEQUENCE: tuple[Regime, ...] = ("risk_off", "neutral", "risk_on")


class WorldStateSnapshot(FormalObjectBase):
    """L4 formal shared market state."""

    cycle_id: CycleId
    baseline_regime: Regime
    llm_delta: Literal[-1, 0, 1]
    final_regime: Regime
    llm_rationale: str
    actual_model_used: str
    actual_provider: str
    fallback_path: list[str]

    @model_validator(mode="after")
    def validate_final_regime(self) -> WorldStateSnapshot:
        baseline_index = _REGIME_SEQUENCE.index(self.baseline_regime)
        final_index = baseline_index + self.llm_delta

        if final_index < 0 or final_index >= len(_REGIME_SEQUENCE):
            raise ValueError("baseline_regime + llm_delta falls outside the regime sequence")

        expected_final_regime = _REGIME_SEQUENCE[final_index]
        if self.final_regime != expected_final_regime:
            raise ValueError(
                "final_regime must equal baseline_regime shifted by llm_delta "
                f"({expected_final_regime!r})"
            )

        return self
