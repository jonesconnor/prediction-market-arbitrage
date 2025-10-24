from __future__ import annotations

import json
from datetime import datetime, timezone
import logging
from typing import Any, Iterable, List

from .models import Market, Outcome

logger = logging.getLogger(__name__)


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


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            return list(parsed) if isinstance(parsed, Iterable) else []
        except json.JSONDecodeError:
            return []
    if isinstance(value, Iterable):
        return list(value)
    return []


def _parse_outcomes(raw: dict[str, Any]) -> list[Outcome]:
    names_raw = raw.get("outcomes") or raw.get("contracts")
    prices_raw = raw.get("outcomePrices") or raw.get("prices")
    tokens_raw = (
        raw.get("outcomeTokenIds")
        or raw.get("outcomeTokenIDs")
        or raw.get("outcomeTokens")
        or raw.get("tokens")
        or raw.get("assetIds")
    )

    names = _as_list(names_raw)
    prices = _as_list(prices_raw)
    tokens = _as_list(tokens_raw)

    outcomes: list[Outcome] = []
    for index, name in enumerate(names):
        if not name:
            continue
        price_value = prices[index] if index < len(prices) else None
        token_value = tokens[index] if index < len(tokens) else None
        token_id = str(token_value) if token_value not in {None, ""} else None
        outcomes.append(
            Outcome(
                name=str(name),
                price=_to_float(price_value),
                token_id=token_id,
            )
        )

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
        logger.debug('Skipping market %s due to missing outcomes', market_id)
        return None

    missing_tokens = [outcome.name for outcome in outcomes if not outcome.token_id]
    if missing_tokens:
        logger.debug('Market %s missing token ids for outcomes: %s', market_id, missing_tokens)

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

    condition_id = (
        raw.get("conditionId")
        or raw.get("condition_id")
        or raw.get("marketHash")
        or raw.get("market_hash")
    )

    market_model = Market(
        id=str(market_id),
        question=question,
        url=_build_url(raw, str(market_id)),
        outcomes=outcomes,
        rules_url=rules_url,
        category=category,
        close_time=close_time,
        liquidity=liquidity if liquidity > 0 else None,
        condition_id=str(condition_id) if condition_id else None,
    )

    return market_model
