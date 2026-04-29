"""Unit tests for main-core's graph-engine adapter."""

from __future__ import annotations

import pytest

from main_core.adapters.graph_engine import (
    PlaceholderRegimeContextReader,
    build_regime_context_reader_from_env,
)


def test_placeholder_returns_neutral_multipliers_with_echoed_world_state_ref() -> None:
    reader = PlaceholderRegimeContextReader()
    context = reader.read_regime_context("world-state:CYCLE_20260429:abc")

    assert context["world_state_ref"] == "world-state:CYCLE_20260429:abc"
    assert context["channel_multipliers"] == {
        "fundamental": 1.0,
        "event": 1.0,
        "reflexive": 1.0,
    }
    assert context["regime_multipliers"] == {
        "fundamental": 1.0,
        "event": 1.0,
        "reflexive": 1.0,
    }
    assert context["decay_policy"] == {"default": 1.0}


def test_placeholder_dict_shape_matches_graph_engine_static_fake() -> None:
    """Pin the keys so this adapter stays drop-in compatible with
    graph-engine's existing test fake (StaticRegimeReader)."""

    reader = PlaceholderRegimeContextReader()
    context = reader.read_regime_context("ws-1")
    assert frozenset(context.keys()) == frozenset(
        {"world_state_ref", "channel_multipliers", "regime_multipliers", "decay_policy"}
    )


def test_placeholder_accepts_custom_channels_and_multiplier() -> None:
    reader = PlaceholderRegimeContextReader(
        channels=("fundamental",),
        default_multiplier=0.75,
    )
    context = reader.read_regime_context("ws-2")

    assert context["channel_multipliers"] == {"fundamental": 0.75}
    assert context["regime_multipliers"] == {"fundamental": 0.75}
    assert context["decay_policy"] == {"default": 0.75}


def test_placeholder_rejects_negative_multiplier() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        PlaceholderRegimeContextReader(default_multiplier=-0.1)


def test_factory_returns_placeholder_instance() -> None:
    reader = build_regime_context_reader_from_env()
    assert isinstance(reader, PlaceholderRegimeContextReader)


def test_factory_returns_independent_instances() -> None:
    """Each call returns a fresh instance — no global singleton leaks."""

    a = build_regime_context_reader_from_env()
    b = build_regime_context_reader_from_env()
    assert a is not b
