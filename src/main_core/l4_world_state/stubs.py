"""P2 world-state policy stubs for L4."""

from __future__ import annotations

from main_core.common.contexts import WorldStateInputs
from main_core.common.protocols import BoundedLlmDelta, WorldStatePolicyBase
from main_core.common.types import Regime


class DefaultWorldStatePolicyStub(WorldStatePolicyBase):
    """P2 placeholder, wired in milestone-2."""

    def baseline(self, inputs: WorldStateInputs) -> Regime:
        """Reserve baseline regime selection for the real L4 implementation."""

        raise NotImplementedError("implemented in #7")

    def bound_delta(self, raw_delta: int) -> BoundedLlmDelta:
        """Clamp raw LLM deltas to the hard formal ``-1`` / ``0`` / ``+1`` range."""

        if raw_delta < 0:
            return -1
        if raw_delta > 0:
            return 1
        return 0

    def compose(self, baseline: Regime, delta: BoundedLlmDelta) -> Regime:
        """Reserve final regime composition for the real L4 implementation."""

        raise NotImplementedError("implemented in #7")


__all__ = ["DefaultWorldStatePolicyStub"]
