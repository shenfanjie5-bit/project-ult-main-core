"""P2 single-prompt alpha analyzer implementation."""

from __future__ import annotations

from math import isfinite
from typing import ClassVar

from main_core.common.contexts import AlphaAnalysisContext
from main_core.common.errors import MainCoreError
from main_core.common.protocols import AnalyzerBase
from main_core.common.schemas import AlphaResultSnapshot, single_prompt_result
from main_core.common.types import EntityId
from main_core.l6_alpha.errors import AlphaAnalyzerError, AlphaReasonerError
from main_core.l6_alpha.fallback import (
    build_inconclusive_result,
    is_task_level_failure,
)
from main_core.l6_alpha.reasoner_port import (
    AlphaReasonerPort,
    AlphaReasonerResponse,
    StaticAlphaReasonerPort,
)


class SinglePromptAnalyzer(AnalyzerBase):
    """P2 single-prompt analyzer for one official alpha pool entity."""

    analyzer_type: ClassVar[str] = "single_prompt_v1"

    def __init__(self, reasoner_port: AlphaReasonerPort | None = None) -> None:
        self._reasoner_port = reasoner_port or StaticAlphaReasonerPort()

    def analyze(
        self,
        entity_id: EntityId,
        context: AlphaAnalysisContext,
    ) -> AlphaResultSnapshot:
        """Analyze one entity and downgrade only task-level failures."""

        if entity_id != context.entity_id:
            raise AlphaAnalyzerError("entity_id must match context.entity_id")

        try:
            response = self._reasoner_port.analyze_alpha(entity_id, context)
        except Exception as exc:
            if is_task_level_failure(exc):
                return build_inconclusive_result(entity_id, context, str(exc))
            if isinstance(exc, MainCoreError):
                raise
            raise AlphaReasonerError("alpha reasoner failed") from exc

        if response.task_failed:
            reason = response.failure_reason or response.rationale or "alpha task failed"
            return build_inconclusive_result(
                entity_id,
                context,
                reason,
                similar_cases=response.similar_cases,
            )

        _validate_successful_response(response)
        return single_prompt_result(
            cycle_id=context.cycle_id,
            entity_id=entity_id,
            score=response.score,
            confidence=response.confidence,
            rationale=response.rationale,
            similar_cases=response.similar_cases,
            status="ok",
        )


def _validate_successful_response(response: AlphaReasonerResponse) -> None:
    if response.score is None or not isfinite(response.score):
        raise AlphaReasonerError("successful alpha response score must be finite")
    if not isfinite(response.confidence) or not 0.0 <= response.confidence <= 1.0:
        raise AlphaReasonerError(
            "successful alpha response confidence must be finite and within 0.0..1.0"
        )
    if not response.rationale.strip():
        raise AlphaReasonerError("successful alpha response rationale must be non-empty")


__all__ = ["AlphaAnalyzerError", "SinglePromptAnalyzer"]
