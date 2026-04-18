"""P2 single-prompt alpha analyzer implementation."""

from __future__ import annotations

from math import isfinite
from typing import ClassVar

from main_core.common.contexts import AlphaAnalysisContext
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

        _validate_context(entity_id, context)

        try:
            response = self._reasoner_port.analyze_alpha(entity_id, context)
        except Exception as exc:
            if is_task_level_failure(exc):
                return build_inconclusive_result(entity_id, context, str(exc))
            raise AlphaReasonerError(
                f"alpha reasoner provider failed: {exc}"
            ) from exc

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


def _validate_context(entity_id: EntityId, context: AlphaAnalysisContext) -> None:
    if entity_id != context.entity_id:
        raise AlphaAnalyzerError("entity_id must match context.entity_id")
    if context.feature_bundle.cycle_id != context.cycle_id:
        raise AlphaAnalyzerError("feature_bundle.cycle_id must match context.cycle_id")
    if context.world_state.cycle_id != context.cycle_id:
        raise AlphaAnalyzerError("world_state.cycle_id must match context.cycle_id")
    if context.feature_bundle.entity_id != context.entity_id:
        raise AlphaAnalyzerError("feature_bundle.entity_id must match context.entity_id")


def _validate_successful_response(response: AlphaReasonerResponse) -> None:
    _finite_number(response.score, "score")
    confidence = _finite_number(response.confidence, "confidence")
    if not 0.0 <= confidence <= 1.0:
        raise AlphaReasonerError("alpha reasoner confidence must be within 0.0..1.0")
    if not isinstance(response.rationale, str) or not response.rationale.strip():
        raise AlphaReasonerError("alpha reasoner rationale must be non-empty")


def _finite_number(value: object, field_name: str) -> float:
    if (
        not isinstance(value, int | float)
        or isinstance(value, bool)
        or not isfinite(value)
    ):
        raise AlphaReasonerError(f"alpha reasoner {field_name} must be finite numeric")
    return float(value)


__all__ = ["AlphaAnalyzerError", "SinglePromptAnalyzer"]
