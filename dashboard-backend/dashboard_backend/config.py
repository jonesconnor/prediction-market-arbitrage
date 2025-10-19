from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gamma_url: str = Field(
        default="https://gamma-api.polymarket.com/markets",
        alias="PM_GAMMA_URL",
        description="Base URL for the Polymarket Gamma markets REST API.",
    )
    clob_ws: str = Field(
        default="wss://clob.polymarket.com/ws",
        alias="PM_CLOB_WS",
        description="WebSocket endpoint for the Polymarket CLOB (reserved for future use).",
    )
    min_edge: float = Field(
        default=0.01,
        alias="MIN_EDGE",
        description="Minimum edge (1 - sum of outcome prices) required to surface an opportunity.",
    )
    min_liquidity: float = Field(
        default=100.0,
        alias="MIN_LIQUIDITY",
        description="Minimum market liquidity threshold in USD for opportunities.",
    )
    rest_refresh_sec: int = Field(
        default=30,
        alias="REST_REFRESH_SEC",
        description="Polling cadence for refreshing Gamma market data, in seconds.",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
        description="Redis connection URL for caching and pub/sub.",
    )
    redis_history_cap: int = Field(
        default=2880,
        alias="REDIS_HISTORY_CAP",
        description="Maximum number of history points to retain per market (e.g., 24h at 30s).",
    )
    gamma_limit: int = Field(
        default=200,
        alias="PM_GAMMA_LIMIT",
        description="Maximum number of markets to request per Gamma poll.",
    )
    request_timeout: float = Field(
        default=10.0,
        alias="REST_TIMEOUT_SEC",
        description="Timeout in seconds for Gamma REST requests.",
    )
    cors_allow_origins: str = Field(
        default="*",
        alias="CORS_ALLOW_ORIGINS",
        description="Comma-separated list of origins allowed for CORS (use '*' for all).",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()


settings = get_settings()
