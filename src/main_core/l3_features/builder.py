"""Feature signal bundle builder for the L3 layer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from main_core.common.schemas.feature_bundle import FeatureSignalBundle
from main_core.common.types import CycleId, EntityId
from main_core.l1_l2_basis.models import MarketBar
from main_core.l1_l2_basis.ports import DataPlatformPort
from main_core.l1_l2_basis.readers import read_entity_master, read_market_bars
from main_core.l3_features.feature_math import (
    apply_feature_weight_multiplier,
    market_bar_feature_values,
)
from main_core.l3_features.multiplier_store import MultiplierStore
from main_core.l3_features.weight_api import get_feature_weight_multiplier


def build_feature_signal_bundle(
    cycle_id: CycleId | str,
    *,
    data_port: DataPlatformPort,
    multiplier_store: MultiplierStore | None = None,
    graph_impact: Mapping[str, Mapping[str, Any]] | None = None,
    candidate_signals: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[FeatureSignalBundle]:
    """Build one feature signal bundle per active entity with market data."""

    entity_master = read_entity_master(cycle_id, port=data_port)
    market_bars = read_market_bars(cycle_id, port=data_port)
    active_entity_ids = {
        str(entity.entity_id)
        for entity in entity_master
        if entity.is_active
    }
    latest_bars = _latest_market_bars_by_entity(market_bars)
    multipliers = get_feature_weight_multiplier(cycle_id, store=multiplier_store)

    bundles: list[FeatureSignalBundle] = []
    for entity_id in sorted(active_entity_ids):
        market_bar = latest_bars.get(entity_id)
        if market_bar is None:
            continue

        base_feature_values = market_bar_feature_values(market_bar)
        feature_values, effective_multipliers = apply_feature_weight_multiplier(
            base_feature_values,
            multipliers,
        )
        bundles.append(
            FeatureSignalBundle(
                cycle_id=cycle_id,
                entity_id=EntityId(entity_id),
                feature_values=feature_values,
                signal_values=dict((candidate_signals or {}).get(entity_id, {})),
                graph_features=dict((graph_impact or {}).get(entity_id, {})),
                feature_weight_multiplier=effective_multipliers,
            )
        )

    return bundles


def _latest_market_bars_by_entity(market_bars: list[MarketBar]) -> dict[str, MarketBar]:
    latest_bars: dict[str, MarketBar] = {}
    for market_bar in market_bars:
        entity_id = str(market_bar.entity_id)
        previous_bar = latest_bars.get(entity_id)
        if previous_bar is None or market_bar.as_of_date > previous_bar.as_of_date:
            latest_bars[entity_id] = market_bar
    return latest_bars


__all__ = ["build_feature_signal_bundle"]
