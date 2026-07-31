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
REGISTER_PATH = "/v1/internal/telegram/register"
ME_PATH = "/v1/internal/telegram/me"
LEADERBOARD_PATH = "/v1/internal/telegram/leaderboard"


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


class RegistrationConsentRequiredError(ApiClientError):
    """The API returned 409 {error: consent_required} for POST /register.

    FR-BOT-002 PR 2/6: this event requires EULA acceptance, which the bot
    does not yet collect (see 01-requirement-validation.md's finding — the
    web UI has no mature consent-prompt flow to mirror either). Handlers
    show a plain fallback message pointing to the web instead of crashing.
    """


class RegistrationIneligibleError(ApiClientError):
    """The API returned 409 {error: registration_ineligible} for POST /register."""


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


@dataclass(frozen=True, slots=True)
class RegisterResult:
    """Mirrors the API's `TelegramRegisterResult` response shape.

    `status` is the same union RegistrationsDirectusService returns
    ('registered' | 'waitlisted' | 'cancelled' | 'attended') — the bot
    renders two distinct confirmation messages for 'registered' vs.
    'waitlisted' (FR-BOT-002 PR 2/6 AC-1/AC-2); the other two values are
    not reachable from a successful register call in practice but are
    included for type-shape fidelity with the API's own union.
    """

    status: str
    event_title: str


@dataclass(frozen=True, slots=True)
class CancelResult:
    """Mirrors the API's `TelegramCancelResult` response shape.

    status == 'not_registered' is NOT an error — it's the API's own signal
    for "no active registration existed to cancel," surfaced as a plain
    result rather than an exception (mirrors RegistrationsDirectusService
    .cancel() returning null rather than throwing for the same case).
    """

    status: str


@dataclass(frozen=True, slots=True)
class MeRegistrationEvent:
    """Mirrors one `TelegramMeRegistrationEvent` entry from the API."""

    id: str
    title: str
    starts_at: str
    ends_at: str
    location: str | None


@dataclass(frozen=True, slots=True)
class MeRegistration:
    """Mirrors one `TelegramMeRegistration` entry from the API.

    `status` is the same union register()/cancel() already use
    ('registered' | 'waitlisted' | 'attended' in practice here —
    'cancelled' rows are excluded server-side by listMine's own filter,
    so the bot never receives one to render a badge for).
    """

    id: str
    status: str
    event: MeRegistrationEvent


@dataclass(frozen=True, slots=True)
class MeSummary:
    """Mirrors the API's `TelegramMeResult` response shape (FR-BOT-002
    PR 3/6). Deliberately has no streak/account-type/link-status fields —
    account type comes from the caller's own UserContext.is_temp (already
    resolved by AuthMiddleware), the link CTA is static copy, and streak
    does not exist anywhere in this codebase yet (see
    01-requirement-validation.md in wf-20260801-feat-176 for the full
    reasoning — a documented scope gap, not an oversight).
    """

    registrations: list[MeRegistration] = field(default_factory=list)
    points_total: int = 0


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """Mirrors one `TelegramLeaderboardEntry` entry from the API.

    No email/handle fields — the API deliberately narrows the response to
    what a leaderboard render needs (see 02-impact-analysis.md's PII risk
    flag); the bot has nothing further to redact.
    """

    display_name: str
    points: int
    is_caller: bool


@dataclass(frozen=True, slots=True)
class LeaderboardResult:
    """Mirrors the API's `TelegramLeaderboardResult` response shape
    (FR-BOT-002 PR 4/6). At most one entry has is_caller=True — isCaller
    is resolved API-side (see telegram-auth.service.ts's getLeaderboard),
    so the bot only needs to read the flag, never compute it.
    """

    entries: list[LeaderboardEntry] = field(default_factory=list)


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

    async def register_for_event(
        self, *, directus_user_id: str, event_id: str, country: str
    ) -> RegisterResult:
        """Register via POST /v1/internal/telegram/register.

        FEAT-BOT-2 (FR-BOT-002 PR 2/6). Duplicate registration is NOT an
        error — RegistrationsDirectusService.register() returns the
        existing row idempotently, so a repeat call here just returns the
        same status again (confirmed live against the local stack).

        Raises:
            EventNotFoundError: API returned 404 (no such published event
                or the event isn't available in this country).
            RegistrationConsentRequiredError: API returned 409
                {error: consent_required} — this event needs EULA
                acceptance, which the bot doesn't collect yet.
            RegistrationIneligibleError: API returned 409
                {error: registration_ineligible} (e.g. account not yet
                linked to Directus).
            ApiUnavailableError: any other non-2xx response, network error,
                or timeout.
        """
        url = f"{self._base_url}{REGISTER_PATH}"
        try:
            response = await self._client.post(
                url,
                json={
                    "directusUserId": directus_user_id,
                    "eventId": event_id,
                    "country": country,
                },
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"register_for_event request failed: {exc}") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise EventNotFoundError(event_id)
        if response.status_code == httpx.codes.CONFLICT:
            error = response.json().get("error")
            if error == "consent_required":
                raise RegistrationConsentRequiredError(event_id)
            raise RegistrationIneligibleError(event_id)
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from register endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return RegisterResult(status=body["status"], event_title=body.get("eventTitle", ""))

    async def cancel_registration(
        self, *, directus_user_id: str, event_id: str, country: str
    ) -> CancelResult:
        """Cancel via DELETE /v1/internal/telegram/register.

        FEAT-BOT-2 (FR-BOT-002 PR 2/6). `status: 'not_registered'` is a
        normal result, not an exception — see CancelResult's docstring.
        Waitlist promotion (if any) is handled entirely by the existing
        Directus flow; this call does not surface promotion details.

        Raises:
            EventNotFoundError: API returned 404 (no such published event
                or the event isn't available in this country).
            ApiUnavailableError: any other non-2xx response, network error,
                or timeout.
        """
        url = f"{self._base_url}{REGISTER_PATH}"
        try:
            response = await self._client.request(
                "DELETE",
                url,
                json={
                    "directusUserId": directus_user_id,
                    "eventId": event_id,
                    "country": country,
                },
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"cancel_registration request failed: {exc}") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise EventNotFoundError(event_id)
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from cancel endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return CancelResult(status=body["status"])

    async def get_me_summary(self, *, directus_user_id: str, country: str) -> MeSummary:
        """Fetch the caller's /me summary via GET /v1/internal/telegram/me.

        FEAT-BOT-2 (FR-BOT-002 PR 3/6). Aggregates active registrations +
        lifetime points total in one round trip. No 404 case is mapped
        here (unlike lookup_telegram_user) — the bot only calls this once
        AuthMiddleware has already confirmed user_context.is_known and
        resolved a directus_user_id, so an unresolvable identity at this
        point would indicate the bridge itself is broken, which the
        generic ApiUnavailableError path below already covers by treating
        any non-200 as unavailable.

        Raises:
            ApiUnavailableError: any non-2xx response, network error, or
                timeout.
        """
        url = f"{self._base_url}{ME_PATH}"
        try:
            response = await self._client.get(
                url,
                params={"directusUserId": directus_user_id, "country": country},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"get_me_summary request failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from me endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        registrations = [
            MeRegistration(
                id=item["id"],
                status=item["status"],
                event=MeRegistrationEvent(
                    id=item["event"]["id"],
                    title=item["event"]["title"],
                    starts_at=item["event"]["startsAt"],
                    ends_at=item["event"]["endsAt"],
                    location=item["event"].get("location"),
                ),
            )
            for item in body.get("registrations", [])
        ]
        return MeSummary(registrations=registrations, points_total=body.get("pointsTotal", 0))

    async def get_leaderboard(self, *, directus_user_id: str, country: str) -> LeaderboardResult:
        """Fetch the top-10 country leaderboard via
        GET /v1/internal/telegram/leaderboard.

        FEAT-BOT-2 (FR-BOT-002 PR 4/6). `directus_user_id` is required (not
        optional, unlike get_event_detail's) — the API needs it to resolve
        isCaller per row; the bot only calls this once AuthMiddleware has
        already confirmed a known identity, same precondition
        get_me_summary already assumes.

        Raises:
            ApiUnavailableError: any non-2xx response, network error, or
                timeout.
        """
        url = f"{self._base_url}{LEADERBOARD_PATH}"
        try:
            response = await self._client.get(
                url,
                params={"directusUserId": directus_user_id, "country": country},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"get_leaderboard request failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from leaderboard endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        entries = [
            LeaderboardEntry(
                display_name=item["displayName"],
                points=item["points"],
                is_caller=bool(item.get("isCaller", False)),
            )
            for item in body.get("entries", [])
        ]
        return LeaderboardResult(entries=entries)
