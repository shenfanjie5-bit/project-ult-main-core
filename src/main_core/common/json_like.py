"""Shared JSON-like payload normalization helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def to_plain_json_like(value: Any) -> Any:
    """Return a recursively plain JSON-like value for schema/report payloads."""

    if isinstance(value, Mapping):
        return {
            str(key): to_plain_json_like(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [to_plain_json_like(item) for item in value]
    if isinstance(value, frozenset | set):
        return sorted(to_plain_json_like(item) for item in value)
    return value


__all__ = ["to_plain_json_like"]
