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
        default="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        alias="PM_CLOB_WS",
        description="WebSocket endpoint for the Polymarket CLOB (reserved for future use).",
    )
    clob_host: str = Field(
        default="https://clob.polymarket.com",
        alias="PM_CLOB_HOST",
        description="Base HTTP host for the Polymarket CLOB REST API.",
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
    enable_ws_ingest: bool = Field(
        default=True,
        alias="ENABLE_WS_INGEST",
        description="Toggle for subscribing to the Polymarket market websocket feed.",
    )
    ws_ping_interval: float = Field(
        default=10.0,
        alias="WS_PING_INTERVAL",
        description="Seconds between websocket ping messages.",
    )
    ws_subscribe_chunk_size: int = Field(
        default=200,
        alias="WS_SUBSCRIBE_CHUNK_SIZE",
        description="Number of asset ids to include per subscription payload.",
    )
    ws_reconnect_backoff: float = Field(
        default=5.0,
        alias="WS_RECONNECT_BACKOFF",
        description="Initial backoff seconds before attempting websocket reconnects.",
    )
    ws_verify_ssl: bool = Field(
        default=True,
        alias="WS_VERIFY_SSL",
        description="Whether to verify SSL certificates when connecting to the Polymarket market websocket.",
    )



@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()


settings = get_settings()
