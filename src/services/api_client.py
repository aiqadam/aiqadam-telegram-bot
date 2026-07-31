"""HTTP client wrapper for the NestJS internal API.

The bot is thin by design (FR-BOT-001, ADR-0034 §Q3): it holds no business
state and calls the API for everything. This module is the ONLY place that
issues HTTP requests to `INTERNAL_API_URL`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

LOOKUP_PATH = "/v1/internal/telegram/lookup"
EVENTS_PATH = "/v1/internal/telegram/events"


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


class EventNotFoundError(ApiClientError):
    """The API returned 404 for GET /events/:id — no such published event."""


@dataclass(frozen=True, slots=True)
class EventListItem:
    """Mirrors one item of the API's `TelegramEventListResult.items`."""

    id: str
    title: str
    starts_at: str
    registration_count: int


@dataclass(frozen=True, slots=True)
class EventListResult:
    """Mirrors the API's `TelegramEventListResult` response shape."""

    items: list[EventListItem] = field(default_factory=list)
    offset: int = 0
    limit: int = 0
    total: int = 0


@dataclass(frozen=True, slots=True)
class EventDetail:
    """Mirrors the API's `TelegramEventDetailResult` response shape."""

    id: str
    title: str
    starts_at: str
    venue: str | None
    description: str
    capacity: int | None
    registration_count: int
    is_registered: bool


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

    async def list_events(
        self, country: str, *, offset: int = 0, limit: int = 5
    ) -> EventListResult:
        """List upcoming events via GET /v1/internal/telegram/events.

        FEAT-BOT-2 (FR-BOT-002 PR 1/6). Offset-based pagination — the
        /events handler renders "Next page ->" / "<- Previous page" from
        `offset`/`limit`/`total`.

        Raises:
            ApiUnavailableError: non-2xx response, network error, or timeout.
        """
        url = f"{self._base_url}{EVENTS_PATH}"
        try:
            response = await self._client.get(
                url,
                params={"country": country, "offset": offset, "limit": limit},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"list_events request failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from events endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        items = [
            EventListItem(
                id=item["id"],
                title=item["title"],
                starts_at=item["startsAt"],
                registration_count=item.get("registrationCount", 0),
            )
            for item in body.get("items", [])
        ]
        return EventListResult(
            items=items,
            offset=body.get("offset", offset),
            limit=body.get("limit", limit),
            total=body.get("total", len(items)),
        )

    async def get_event_detail(
        self, event_id: str, *, directus_user_id: str | None = None
    ) -> EventDetail:
        """Fetch one event's detail via GET /v1/internal/telegram/events/:id.

        FEAT-BOT-2 (FR-BOT-002 PR 1/6). `directus_user_id` is optional —
        only used by the API to annotate `is_registered`; the bot passes it
        whenever `user_context.directus_user_id` is available.

        Raises:
            EventNotFoundError: API returned 404 (no such published event).
            ApiUnavailableError: any other non-2xx response, network error,
                or timeout.
        """
        url = f"{self._base_url}{EVENTS_PATH}/{event_id}"
        params = {"directusUserId": directus_user_id} if directus_user_id else {}
        try:
            response = await self._client.get(
                url,
                params=params,
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"get_event_detail request failed: {exc}") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise EventNotFoundError(event_id)

        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from event detail endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return EventDetail(
            id=body["id"],
            title=body["title"],
            starts_at=body["startsAt"],
            venue=body.get("venue"),
            description=body.get("description", ""),
            capacity=body.get("capacity"),
            registration_count=body.get("registrationCount", 0),
            is_registered=bool(body.get("isRegistered", False)),
        )
