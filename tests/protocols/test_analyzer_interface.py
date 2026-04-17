"""Tests for the L6 analyzer protocol contract."""

from __future__ import annotations

from inspect import signature

from main_core.common.contexts import AlphaAnalysisContext
from main_core.common.protocols import AnalyzerBase, AnalyzerInterface
from main_core.common.schemas import FeatureSignalBundle, WorldStateSnapshot
from main_core.l6_alpha import AlphaReasonerResponse, SinglePromptAnalyzer, StaticAlphaReasonerPort

CYCLE_ID = "cycle_001"
ENTITY_ID = "ENT_001"
SINGLE_PROMPT_ANALYZER = "single_prompt_v1"


def _feature_bundle() -> FeatureSignalBundle:
    return FeatureSignalBundle(
        cycle_id=CYCLE_ID,
        entity_id=ENTITY_ID,
        feature_values={"momentum": 0.42},
        signal_values={"signal": "positive"},
        graph_features={},
        feature_weight_multiplier={"momentum": 1.0},
    )


def _world_state() -> WorldStateSnapshot:
    return WorldStateSnapshot(
        cycle_id=CYCLE_ID,
        baseline_regime="neutral",
        llm_delta=0,
        final_regime="neutral",
        llm_rationale="stub",
        actual_model_used="none",
        actual_provider="none",
        fallback_path=[],
    )


def _analysis_context() -> AlphaAnalysisContext:
    return AlphaAnalysisContext(
        cycle_id=CYCLE_ID,
        entity_id=ENTITY_ID,
        feature_bundle=_feature_bundle(),
        world_state=_world_state(),
        similar_cases=[],
    )


def test_analyzer_protocol_imports() -> None:
    assert AnalyzerInterface is not None
    assert AnalyzerBase is not None


def test_single_prompt_analyzer_matches_runtime_protocol() -> None:
    analyzer = SinglePromptAnalyzer()

    assert isinstance(analyzer, AnalyzerInterface)
    assert analyzer.analyzer_type == SINGLE_PROMPT_ANALYZER


def test_analyzer_protocol_requires_explicit_entity_argument() -> None:
    expected_parameters = ["self", "entity_id", "context"]

    assert list(signature(AnalyzerInterface.analyze).parameters) == expected_parameters
    assert list(signature(AnalyzerBase.analyze).parameters) == expected_parameters
    assert list(signature(SinglePromptAnalyzer.analyze).parameters) == expected_parameters


def test_single_prompt_analyzer_returns_single_prompt_result() -> None:
    analyzer = SinglePromptAnalyzer(
        StaticAlphaReasonerPort(
            AlphaReasonerResponse(
                score=0.64,
                confidence=0.72,
                rationale="quality and momentum align",
                similar_cases=[],
            ),
        ),
    )

    result = analyzer.analyze(ENTITY_ID, _analysis_context())

    assert result.analyzer_type == SINGLE_PROMPT_ANALYZER
    assert result.status == "ok"
