"""L4 formal world state schema."""

from __future__ import annotations

from typing import Literal

from main_core.common.schemas.base import FormalObjectBase
from main_core.common.types import CycleId, Regime


class WorldStateSnapshot(FormalObjectBase):
    """Formal L4 shared world state snapshot described in §9.3."""

    cycle_id: CycleId
    baseline_regime: Regime
    llm_delta: Literal[-1, 0, 1]
    final_regime: Regime
    llm_rationale: str
    actual_model_used: str
    actual_provider: str
    fallback_path: list[str]


__all__ = ["WorldStateSnapshot"]
