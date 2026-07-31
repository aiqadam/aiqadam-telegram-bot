"""HTTP client wrapper for the NestJS internal API.

The bot is thin by design (FR-BOT-001, ADR-0034 §Q3): it holds no business
state and calls the API for everything. This module is the ONLY place that
issues HTTP requests to `INTERNAL_API_URL`.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

LOOKUP_PATH = "/v1/internal/telegram/lookup"


class ApiClientError(Exception):
    """Base class for lookup-call failures the caller must handle."""


class TelegramUserNotFoundError(ApiClientError):
    """The API returned 404 — no Authentik user exists for this telegram_id yet."""


class ApiUnavailableError(ApiClientError):
    """The API call failed for any other reason (network, 5xx, timeout, auth)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class LookupResult:
    """Mirrors the API's `LookupUserResult` response shape exactly."""

    directus_user_id: str | None
    is_temp: bool
    country: str | None


class ApiClient:
    """Thin async wrapper around the internal API's bot-facing endpoints."""

    def __init__(
        self,
        base_url: str,
        internal_api_token: str,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = internal_api_token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def lookup_telegram_user(self, telegram_id: str) -> LookupResult:
        """Resolve a telegram_id via POST /v1/internal/telegram/lookup.

        Raises:
            TelegramUserNotFoundError: API returned 404 (unknown telegram_id).
            ApiUnavailableError: any other non-2xx response, network error,
                or timeout — the caller should treat the API as down, not
                the user as unknown.
        """
        url = f"{self._base_url}{LOOKUP_PATH}"
        try:
            response = await self._client.post(
                url,
                json={"telegramId": telegram_id},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"lookup request failed: {exc}") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise TelegramUserNotFoundError(telegram_id)

        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from lookup endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return LookupResult(
            directus_user_id=body.get("directusUserId"),
            is_temp=bool(body.get("isTemp", False)),
            country=body.get("country"),
        )
