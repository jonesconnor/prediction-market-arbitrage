from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Outcome(BaseModel):
    """Normalized market outcome."""

    name: str
    price: float


class Market(BaseModel):
    """Normalized market representation used by the application."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    question: str
    url: str
    outcomes: list[Outcome]
    rules_url: str | None = Field(default=None, alias="rulesUrl")
    category: str | None = None
    close_time: datetime | None = Field(default=None, alias="closeTime")
    liquidity: float | None = None


class Opportunity(BaseModel):
    """Representation of a surfaced underround opportunity."""

    model_config = ConfigDict(populate_by_name=True)

    market_id: str = Field(alias="marketId")
    question: str
    sum_prices: float = Field(alias="sumPrices")
    edge: float
    num_outcomes: int = Field(alias="numOutcomes")
    liquidity: float | None = None
    url: str
    updated_at: datetime = Field(alias="updatedAt")
    category: str | None = None

    def serialize(self) -> dict[str, Any]:
        """Return a dict with API-friendly field names and ISO timestamps."""

        payload = self.model_dump(by_alias=True)
        payload["updatedAt"] = self.updated_at.isoformat()
        return payload


class OpportunityUpdate(BaseModel):
    """Message published to downstream consumers when an opportunity changes."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["upsert", "remove"]
    market_id: str = Field(alias="marketId")
    opportunity: Opportunity | None = None

    def serialize(self) -> dict[str, Any]:
        payload = self.model_dump(by_alias=True)
        if self.opportunity is not None:
            payload["opportunity"] = self.opportunity.serialize()
        return payload
