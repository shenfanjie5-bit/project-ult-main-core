"""Shared deterministic L7 recommendation rules."""

from __future__ import annotations

BUY_SCORE_THRESHOLD = 0.65
REDUCE_SCORE_THRESHOLD = 0.35

_RATING_BY_ACTION = {
    "buy": "A",
    "hold": "B",
    "reduce": "C",
}


def action_for_score(score: float) -> str:
    """Map an alpha score to the deterministic recommendation action."""

    if score >= BUY_SCORE_THRESHOLD:
        return "buy"
    if score <= REDUCE_SCORE_THRESHOLD:
        return "reduce"
    return "hold"


def rating_for_action(action_type: str) -> str:
    """Map a non-inconclusive action to the formal rating value."""

    return _RATING_BY_ACTION[action_type]


__all__ = [
    "BUY_SCORE_THRESHOLD",
    "REDUCE_SCORE_THRESHOLD",
    "action_for_score",
    "rating_for_action",
]
