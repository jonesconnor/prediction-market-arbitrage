from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

from .models import Market, Outcome


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.endswith("Z"):
            candidate = candidate.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            return None

    return None


def _build_url(raw: dict[str, Any], market_id: str) -> str:
    if url := raw.get("url"):
        return url
    if slug := raw.get("slug"):
        return f"https://polymarket.com/event/{slug}"
    return f"https://polymarket.com/event/{market_id}"


def _parse_outcomes(raw: dict[str, Any]) -> list[Outcome]:
    names_raw = raw.get("outcomes") or raw.get("contracts")
    prices_raw = raw.get("outcomePrices") or raw.get("prices")

    names: Iterable[Any]
    prices: Iterable[Any]

    if isinstance(names_raw, str):
        try:
            names = json.loads(names_raw)
        except json.JSONDecodeError:
            names = []
    elif isinstance(names_raw, Iterable):
        names = names_raw
    else:
        names = []

    if isinstance(prices_raw, str):
        try:
            prices = json.loads(prices_raw)
        except json.JSONDecodeError:
            prices = []
    elif isinstance(prices_raw, Iterable):
        prices = prices_raw
    else:
        prices = []

    outcomes: list[Outcome] = []
    for name, price in zip(names, prices):
        if not name:
            continue
        outcomes.append(Outcome(name=str(name), price=_to_float(price)))

    return outcomes


def normalize_market(raw: dict[str, Any]) -> Market | None:
    """Convert a Gamma market payload into the normalized Market model."""

    market_id = raw.get("id") or raw.get("_id") or raw.get("market_id")
    if not market_id:
        return None

    question = raw.get("question") or raw.get("title")
    if not question:
        return None

    outcomes = _parse_outcomes(raw)

    if not outcomes:
        return None

    rules_url = raw.get("rules") or raw.get("rulesUrl")
    category = raw.get("category") or raw.get("subcategory")
    close_time = _parse_datetime(
        raw.get("closeTime")
        or raw.get("closeDate")
        or raw.get("endDate")
        or raw.get("closesAt")
    )

    liquidity = _to_float(
        raw.get("liquidity")
        or raw.get("liquidity24hr")
        or raw.get("liquidityNum")
        or 0.0
    )

    return Market(
        id=str(market_id),
        question=question,
        url=_build_url(raw, str(market_id)),
        outcomes=outcomes,
        rules_url=rules_url,
        category=category,
        close_time=close_time,
        liquidity=liquidity if liquidity > 0 else None,
    )
