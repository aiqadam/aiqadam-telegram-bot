"""Typed bot configuration, loaded from environment variables only.

Thin-bot guarantee (FR-BOT-001 AC-10, FEAT-BOT-1 AC-10): this module must
NEVER reference DIRECTUS_TOKEN, AUTHENTIK_API_TOKEN, or TWENTY_API_TOKEN.
The bot holds only its own three credentials; every other integration is
reached indirectly via the NestJS API using INTERNAL_API_TOKEN.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SQLITE_PATH = "data/bot-cache.sqlite3"


class Settings(BaseSettings):
    """Bot runtime configuration.

    Values are read from environment variables (or a local `.env` file in
    dev — never committed, see `.env.example`). No other configuration
    source is supported; this keeps the thin-bot guarantee auditable by
    grepping this one file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    internal_api_url: str = Field(alias="INTERNAL_API_URL")
    internal_api_token: str = Field(alias="INTERNAL_API_TOKEN")

    sqlite_path: str = Field(default=DEFAULT_SQLITE_PATH, alias="BOT_SQLITE_PATH")

    rate_limit_per_minute: int = Field(default=10, alias="BOT_RATE_LIMIT_PER_MINUTE")
    http_timeout_seconds: float = Field(default=5.0, alias="BOT_HTTP_TIMEOUT_SECONDS")

    log_level: str = Field(default="INFO", alias="BOT_LOG_LEVEL")

    @field_validator("internal_api_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def sqlite_full_path(self) -> Path:
        path = Path(self.sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def load_settings() -> Settings:
    """Load settings from the environment.

    Raises pydantic.ValidationError with a clear message if a required
    variable (TELEGRAM_BOT_TOKEN, INTERNAL_API_URL, INTERNAL_API_TOKEN) is
    missing — fail fast at startup rather than at first update.
    """
    return Settings()  # type: ignore[call-arg]  # values come from env/ .env
