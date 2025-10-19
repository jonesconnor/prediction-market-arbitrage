from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from .models import Market, Opportunity


def compute_opportunity(
    market: Market,
    *,
    min_edge: float,
    min_liquidity: float,
) -> Opportunity | None:
    """Return an opportunity when the market meets the configured thresholds."""

    sum_prices = sum(outcome.price for outcome in market.outcomes)
    edge = 1.0 - sum_prices

    liquidity = market.liquidity or 0.0
    if edge < min_edge or liquidity < min_liquidity:
        return None

    return Opportunity(
        market_id=market.id,
        question=market.question,
        sum_prices=sum_prices,
        edge=edge,
        num_outcomes=len(market.outcomes),
        liquidity=market.liquidity,
        url=market.url,
        updated_at=datetime.now(timezone.utc),
        category=market.category,
    )


def compute_opportunities(
    markets: Iterable[Market],
    *,
    min_edge: float,
    min_liquidity: float,
) -> List[Opportunity]:
    """Compute opportunities across a batch of markets."""

    results: List[Opportunity] = []
    for market in markets:
        opportunity = compute_opportunity(
            market,
            min_edge=min_edge,
            min_liquidity=min_liquidity,
        )
        if opportunity:
            results.append(opportunity)
    return results
