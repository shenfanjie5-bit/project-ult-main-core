"""main-core adapter that satisfies graph-engine's ``RegimeContextReader``.

graph-engine Phase 1 propagation needs a regime context — a ``Mapping[str,
Any]`` consumed by ``graph_engine.propagation.context.build_propagation_context``
to scale propagation channel/regime multipliers and the decay policy. The
shape graph-engine expects (per its ``StaticRegimeReader`` test fake) is::

    {
        "world_state_ref": "<echoed-back>",
        "channel_multipliers": {"fundamental": 1.0, "event": 1.0, "reflexive": 1.0},
        "regime_multipliers":  {"fundamental": 1.0, "event": 1.0, "reflexive": 1.0},
        "decay_policy":        {"default": 1.0},
    }

main-core OWNs the formal ``WorldStateSnapshot`` object (``baseline_regime`` /
``llm_delta`` / ``final_regime``) and is therefore the correct owner for the
*business mapping* between regime and propagation multipliers.

**Status: PLACEHOLDER for M2.3a-2.** The actual mapping
(e.g. ``risk_off`` → fundamental = 0.5; ``risk_on`` → fundamental = 1.2)
is a business decision that has not yet been made in any
``project_ult_v5_0_1.md`` / ``ult_milestone.md`` revision. To unblock M2.6
runtime wiring without inventing business policy ad-hoc, this adapter
returns *neutral 1.0 multipliers* regardless of the world state.

This matches the existing ``StaticRegimeReader`` test fake at
``graph-engine/tests/unit/test_phase1_provider.py:56-71``, so swapping it
into M2.6 production wiring preserves the propagation behaviour
graph-engine's tests already validate.

**M2.6 follow-up TODO:** define a ``regime → multipliers`` business
mapping in main-core's L4 service (or a new ``regime_policy.yaml``) and
upgrade this adapter to read the live ``WorldStateSnapshot`` for the
referenced ``world_state_ref``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


_DEFAULT_CHANNELS: tuple[str, ...] = ("fundamental", "event", "reflexive")


class RegimeContextReader(Protocol):
    """Read-only boundary for world-state regime context.

    Mirrors ``graph_engine.propagation.context.RegimeContextReader``; we
    re-declare the Protocol here so main-core does not import graph-engine
    (avoids reverse dependency per graph-engine/CLAUDE.md rule 3).
    """

    def read_regime_context(self, world_state_ref: str) -> Mapping[str, Any]:
        """Return the regime context referenced by a world-state snapshot."""


class PlaceholderRegimeContextReader:
    """Neutral 1.0-multiplier regime context for M2.3a-2 wiring.

    Returns the same shape as graph-engine's ``StaticRegimeReader`` test
    fake. This preserves the graph-engine test contract while leaving the
    business mapping for a follow-up sub-round.
    """

    def __init__(
        self,
        *,
        channels: tuple[str, ...] = _DEFAULT_CHANNELS,
        default_multiplier: float = 1.0,
    ) -> None:
        if default_multiplier < 0.0:
            raise ValueError("default_multiplier must be non-negative")
        self._channels = tuple(channels)
        self._default_multiplier = float(default_multiplier)

    def read_regime_context(self, world_state_ref: str) -> Mapping[str, Any]:
        multipliers = {channel: self._default_multiplier for channel in self._channels}
        return {
            "world_state_ref": world_state_ref,
            "channel_multipliers": dict(multipliers),
            "regime_multipliers": dict(multipliers),
            "decay_policy": {"default": self._default_multiplier},
        }

    @classmethod
    def from_env(cls) -> PlaceholderRegimeContextReader:
        """Construct a neutral placeholder — no env vars consumed yet.

        The real ``WorldStateRegimeContextReader`` (M2.6 follow-up) will
        consume ``DP_PG_DSN`` (or main-core's manifest gateway) to look up
        ``WorldStateSnapshot`` rows.
        """

        return cls()


def build_regime_context_reader_from_env() -> RegimeContextReader:
    """Public factory called by graph-engine's
    ``build_graph_phase1_runtime_from_env``.

    Today: returns a ``PlaceholderRegimeContextReader``. Future: will
    return a ``WorldStateRegimeContextReader`` once the regime → multiplier
    business mapping lands.
    """

    return PlaceholderRegimeContextReader.from_env()


__all__ = [
    "PlaceholderRegimeContextReader",
    "RegimeContextReader",
    "build_regime_context_reader_from_env",
]
