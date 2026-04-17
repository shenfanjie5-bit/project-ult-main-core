"""Formal alpha analysis result schema."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import model_validator

from main_core.common.schemas import FormalObjectBase
from main_core.common.types import CycleId, EntityId

AnalyzerType = Literal["single_prompt_v1", "multi_agent_v1"]
AlphaStatus = Literal["ok", "inconclusive"]


class AlphaResultSnapshot(FormalObjectBase):
    """L6 formal deep analysis result for one entity."""

    cycle_id: CycleId
    entity_id: EntityId
    analyzer_type: AnalyzerType
    score: float | None
    confidence: float
    rationale: str
    similar_cases: list[dict[str, Any]]
    status: AlphaStatus

    @model_validator(mode="after")
    def validate_inconclusive_score(self) -> AlphaResultSnapshot:
        if self.status == "inconclusive" and self.score is not None:
            raise ValueError("inconclusive alpha result must not include a score")
        return self


def single_prompt_result(  # noqa: PLR0913
    *,
    cycle_id: CycleId,
    entity_id: EntityId,
    score: float | None,
    confidence: float,
    rationale: str,
    similar_cases: list[dict[str, Any]],
    status: AlphaStatus = "ok",
) -> AlphaResultSnapshot:
    """Build a P2 default single-prompt alpha result."""
    return AlphaResultSnapshot(
        cycle_id=cycle_id,
        entity_id=entity_id,
        analyzer_type="single_prompt_v1",
        score=score,
        confidence=confidence,
        rationale=rationale,
        similar_cases=similar_cases,
        status=status,
    )
