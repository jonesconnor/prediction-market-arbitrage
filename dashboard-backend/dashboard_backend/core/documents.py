from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MarketDocument(BaseModel):
    """Canonical market snapshot used for cataloging and embeddings."""

    market_id: str = Field(alias="marketId")
    condition_id: str | None = Field(default=None, alias="conditionId")
    question: str
    outcomes: list[str]
    close_time: datetime | None = Field(default=None, alias="closeTime")
    category: str | None = None
    liquidity: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketEmbedding(BaseModel):
    """Stored embedding vector metadata for a market."""

    market_id: str = Field(alias="marketId")
    vector: list[float]
    model: str
    updated_at: datetime = Field(alias="updatedAt")
    signature: str | None = Field(default=None, alias="signature")


__all__ = ["MarketDocument", "MarketEmbedding"]
