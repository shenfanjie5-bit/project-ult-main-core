"""L6 formal alpha analysis result schema."""

from __future__ import annotations

from typing import Any, Literal

from main_core.common.schemas.base import FormalObjectBase
from main_core.common.types import CycleId, EntityId

AnalyzerType = Literal["single_prompt_v1", "multi_agent_v1"]
AlphaStatus = Literal["ok", "inconclusive"]


class AlphaResultSnapshot(FormalObjectBase):
    """Formal L6 alpha result snapshot described in §9.3."""

    cycle_id: CycleId
    entity_id: EntityId
    analyzer_type: AnalyzerType = "single_prompt_v1"
    score: float | None
    confidence: float
    rationale: str
    similar_cases: list[dict[str, Any]]
    status: AlphaStatus


__all__ = ["AlphaResultSnapshot", "AlphaStatus", "AnalyzerType"]
