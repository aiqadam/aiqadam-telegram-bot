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
INTERESTS_PATH = "/v1/internal/telegram/interests"
INTERESTS_TOGGLE_PATH = "/v1/internal/telegram/interests/toggle"
UPGRADE_TEMP_PATH = "/v1/internal/telegram/upgrade-temp"
# FR-BOT-003 operator paths
ATTENDANCE_PATH = "/v1/internal/telegram/attendance/"
OPERATOR_CHECKIN_PATH = "/v1/internal/telegram/operator/checkin"
PENDING_APPROVALS_PATH = "/v1/internal/telegram/operator/pending-approvals"
APPROVE_REGISTRATION_PATH = "/v1/internal/telegram/operator/approve-registration"
DECLINE_REGISTRATION_PATH = "/v1/internal/telegram/operator/decline-registration"
PUSH_ANNOUNCEMENT_PATH = "/v1/internal/telegram/push-announcement"
OPERATOR_STATS_PATH = "/v1/internal/telegram/operator/stats"
# FR-AUTH-005 link paths (public, gated by x-internal-auth service token)
LINK_START_PATH = "/v1/telegram/link/start"
LINK_CONFIRM_PATH = "/v1/telegram/link/confirm"


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
    # FR-BOT-003 — role gate. Null when no role is assigned yet.
    role: str | None = None


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


class NotATempAccountError(ApiClientError):
    """The API returned 409 {error: not_a_temp_account} for POST /upgrade-temp.

    FR-BOT-002 PR 6/6. The caller is already a full member — /upgrade's
    handler normally short-circuits this client-side via
    user_context.is_temp before ever calling the API (see upgrade.py), so
    reaching this exception means a race (the account was upgraded, by
    another /upgrade call or an already-pending magic-link click, between
    the handler's own guard check and this request landing).
    """


class EmailAlreadyInUseError(ApiClientError):
    """The API returned 409 {error: email_already_in_use} for POST /upgrade-temp.

    FR-AUTH-006 AC-7: the supplied email belongs to a different Authentik
    user already. No mutation happened on the API side for this response.
    """


# ── FR-AUTH-005 link-flow exceptions ─────────────────────────────────────────


class LinkMemberNotFoundError(ApiClientError):
    """The API returned 404 member_not_found for POST /link/confirm.

    The email had a valid challenge but no AI Qadam account exists for it.
    The bot informs the user they need to create an account on the web first.
    """


class LinkInvalidCodeError(ApiClientError):
    """The API returned 401 invalid_code for POST /link/confirm.

    Either the code is wrong, the challenge has expired, the challenge
    does not belong to this tg_user_id, or attempts are exhausted.
    The bot prompts the user to try again or restart with /link.
    """


class LinkExhaustedError(ApiClientError):
    """The confirm-attempt ceiling was reached (401 invalid_code after
    MAX_CONFIRM_ATTEMPTS). Distinct from a simple wrong-code to allow
    the bot to tell the user to start over rather than just "try again".
    """


class LinkAlreadyLinkedOtherError(ApiClientError):
    """The API returned 409 already_linked_to_different_account.

    The Directus member account is already linked to a different Telegram
    ID. The bot informs the user they must unlink the other account first.
    """


class LinkRateLimitedError(ApiClientError):
    """The API returned 400 rate_limited for POST /link/start.

    Too many active challenges from this Telegram ID. The bot asks
    the user to wait a few minutes before trying again.
    """


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


@dataclass(frozen=True, slots=True)
class InterestsResult:
    """Mirrors the API's `TelegramInterestsResult` response shape
    (FR-BOT-002 PR 5/6). `selected`/`available` are bare topic_tag slugs —
    label text is resolved bot-side from locales/{ru,en}.py, same as every
    other picker in this bot (no label/icon data crosses the internal API
    boundary; see telegram-auth.service.ts's INTEREST_TOPICS comment).
    """

    selected: list[str] = field(default_factory=list)
    available: list[str] = field(default_factory=list)


# ── FR-BOT-003 operator dataclasses ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AttendanceCounts:
    """Mirrors the API's `TelegramAttendanceResult`."""

    registered: int
    attended: int
    waitlisted: int
    event_title: str


@dataclass(frozen=True, slots=True)
class CheckinResult:
    """Mirrors the API's `OperatorCheckinResult`."""

    member_name: str
    event_title: str
    already_checked_in: bool


class CheckinNotFoundError(ApiClientError):
    """QR code not recognized (API returned 404 checkin_token_not_found)."""


class CheckinIneligibleError(ApiClientError):
    """Registration is not eligible for check-in (cancelled or waitlisted)."""


@dataclass(frozen=True, slots=True)
class PendingApprovalItem:
    """One item from the API's `TelegramPendingApprovalsResult.items`."""

    registration_id: str
    member_name: str
    event_title: str
    event_id: str
    requested_at: str


@dataclass(frozen=True, slots=True)
class PendingApprovalsResult:
    """Mirrors the API's `TelegramPendingApprovalsResult`."""

    items: list[PendingApprovalItem] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PushAnnouncementResult:
    """Mirrors the API's `TelegramPushAnnouncementResult`."""

    recipient_count: int


@dataclass(frozen=True, slots=True)
class OperatorStatsResult:
    """Mirrors the API's `TelegramOperatorStatsResult`."""

    events_managed: int
    registrations_this_period: int


# ── FR-AUTH-005 link-flow dataclasses ────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class LinkStartResult:
    """Mirrors the API's link/start response shape."""

    challenge_id: str
    sent_to_email_masked: str


@dataclass(frozen=True, slots=True)
class LinkConfirmResult:
    """Mirrors the API's link/confirm response shape."""

    member_id: str
    tenant: str


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
            role=body.get("role"),
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

    async def get_interests(self, *, directus_user_id: str) -> InterestsResult:
        """Fetch the caller's topic interests via
        GET /v1/internal/telegram/interests.

        FEAT-BOT-2 (FR-BOT-002 PR 5/6). No `country` param — interests are
        not tenant-scoped (member_interests has no country_code column;
        see telegram-auth.service.ts's interestsQuerySchema comment).

        Raises:
            ApiUnavailableError: any non-2xx response, network error, or
                timeout.
        """
        url = f"{self._base_url}{INTERESTS_PATH}"
        try:
            response = await self._client.get(
                url,
                params={"directusUserId": directus_user_id},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"get_interests request failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from interests endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return InterestsResult(
            selected=list(body.get("selected", [])),
            available=list(body.get("available", [])),
        )

    async def request_upgrade(self, *, telegram_id: str, email: str) -> None:
        """Start a temp-account upgrade via POST /v1/internal/telegram/upgrade-temp.

        FR-BOT-002 PR 6/6, FR-AUTH-006. Success has no payload worth
        modeling — the endpoint always returns `{ok: true}` — so this
        returns None; callers treat "no exception raised" as success,
        matching the pattern lookup_telegram_user's callers already use
        for their own success case (a populated dataclass there vs. plain
        completion here, since there is nothing else to report).

        Raises:
            TelegramUserNotFoundError: API returned 404
                (no Authentik user for this telegram_id — see that
                exception's own docstring; reused here rather than adding
                a duplicate type, since it is the same semantic outcome
                lookup_telegram_user already models).
            NotATempAccountError: API returned 409 {error: not_a_temp_account}.
            EmailAlreadyInUseError: API returned 409 {error: email_already_in_use}.
            ApiUnavailableError: any other non-2xx response, network error,
                or timeout.
        """
        url = f"{self._base_url}{UPGRADE_TEMP_PATH}"
        try:
            response = await self._client.post(
                url,
                json={"telegramId": telegram_id, "email": email},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"request_upgrade request failed: {exc}") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise TelegramUserNotFoundError(telegram_id)
        if response.status_code == httpx.codes.CONFLICT:
            error = response.json().get("error")
            if error == "email_already_in_use":
                raise EmailAlreadyInUseError(email)
            raise NotATempAccountError(telegram_id)
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from upgrade-temp endpoint",
                status_code=response.status_code,
            )

    async def toggle_interest(self, *, directus_user_id: str, topic: str) -> InterestsResult:
        """Toggle one topic interest via
        POST /v1/internal/telegram/interests/toggle.

        FEAT-BOT-2 (FR-BOT-002 PR 5/6). Idempotent single-call toggle —
        the API returns the same {selected, available} shape as
        get_interests, post-toggle, so the handler can re-render in one
        round trip without a second GET.

        Raises:
            ApiUnavailableError: any non-2xx response (including a 400 for
                an out-of-list topic — the bot only ever sends slugs it
                rendered from its own keyboard, so this should not happen
                in practice), network error, or timeout.
        """
        url = f"{self._base_url}{INTERESTS_TOGGLE_PATH}"
        try:
            response = await self._client.post(
                url,
                json={"directusUserId": directus_user_id, "topic": topic},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"toggle_interest request failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from interests toggle endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return InterestsResult(
            selected=list(body.get("selected", [])),
            available=list(body.get("available", [])),
        )

    # ── FR-BOT-003 operator methods ───────────────────────────────────────────

    async def get_attendance(self, *, event_id: str, country: str) -> AttendanceCounts:
        """GET /v1/internal/telegram/attendance/:eventId."""
        url = f"{self._base_url}{ATTENDANCE_PATH}{event_id}"
        try:
            response = await self._client.get(
                url,
                params={"country": country},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"get_attendance request failed: {exc}") from exc
        if response.status_code == httpx.codes.NOT_FOUND:
            raise EventNotFoundError(event_id)
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from attendance endpoint",
                status_code=response.status_code,
            )
        body = response.json()
        return AttendanceCounts(
            registered=int(body.get("registered", 0)),
            attended=int(body.get("attended", 0)),
            waitlisted=int(body.get("waitlisted", 0)),
            event_title=str(body.get("eventTitle", "")),
        )

    async def operator_checkin(self, *, qr_code_data: str, country: str) -> CheckinResult:
        """POST /v1/internal/telegram/operator/checkin."""
        url = f"{self._base_url}{OPERATOR_CHECKIN_PATH}"
        try:
            response = await self._client.post(
                url,
                json={"qrCodeData": qr_code_data, "country": country},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"operator_checkin request failed: {exc}") from exc
        if response.status_code == httpx.codes.NOT_FOUND:
            raise CheckinNotFoundError(qr_code_data)
        if response.status_code == httpx.codes.BAD_REQUEST:
            raise CheckinIneligibleError(response.json().get("message", "ineligible"))
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from operator checkin endpoint",
                status_code=response.status_code,
            )
        body = response.json()
        return CheckinResult(
            member_name=str(body.get("memberName", "")),
            event_title=str(body.get("eventTitle", "")),
            already_checked_in=bool(body.get("alreadyCheckedIn", False)),
        )

    async def list_pending_approvals(
        self, *, country: str, directus_user_id: str
    ) -> PendingApprovalsResult:
        """GET /v1/internal/telegram/operator/pending-approvals."""
        url = f"{self._base_url}{PENDING_APPROVALS_PATH}"
        try:
            response = await self._client.get(
                url,
                params={"country": country, "directusUserId": directus_user_id},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"list_pending_approvals request failed: {exc}") from exc
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from pending-approvals endpoint",
                status_code=response.status_code,
            )
        body = response.json()
        items = [
            PendingApprovalItem(
                registration_id=str(item.get("registrationId", "")),
                member_name=str(item.get("memberName", "")),
                event_title=str(item.get("eventTitle", "")),
                event_id=str(item.get("eventId", "")),
                requested_at=str(item.get("requestedAt", "")),
            )
            for item in body.get("items", [])
        ]
        return PendingApprovalsResult(items=items)

    async def approve_registration(
        self, *, registration_id: str, country: str, directus_user_id: str
    ) -> None:
        """POST /v1/internal/telegram/operator/approve-registration."""
        url = f"{self._base_url}{APPROVE_REGISTRATION_PATH}"
        try:
            response = await self._client.post(
                url,
                json={
                    "registrationId": registration_id,
                    "country": country,
                    "directusUserId": directus_user_id,
                },
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"approve_registration request failed: {exc}") from exc
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from approve-registration endpoint",
                status_code=response.status_code,
            )

    async def decline_registration(
        self, *, registration_id: str, country: str, directus_user_id: str
    ) -> None:
        """POST /v1/internal/telegram/operator/decline-registration."""
        url = f"{self._base_url}{DECLINE_REGISTRATION_PATH}"
        try:
            response = await self._client.post(
                url,
                json={
                    "registrationId": registration_id,
                    "country": country,
                    "directusUserId": directus_user_id,
                },
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"decline_registration request failed: {exc}") from exc
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from decline-registration endpoint",
                status_code=response.status_code,
            )

    async def push_announcement(
        self,
        *,
        event_id: str,
        message: str,
        country: str,
        directus_user_id: str,
    ) -> PushAnnouncementResult:
        """POST /v1/internal/telegram/push-announcement."""
        url = f"{self._base_url}{PUSH_ANNOUNCEMENT_PATH}"
        try:
            response = await self._client.post(
                url,
                json={
                    "eventId": event_id,
                    "message": message,
                    "country": country,
                    "directusUserId": directus_user_id,
                },
                headers={"x-internal-auth": self._token},
                timeout=60.0,  # fan-out can take a few seconds for large events
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"push_announcement request failed: {exc}") from exc
        if response.status_code == httpx.codes.NOT_FOUND:
            raise EventNotFoundError(event_id)
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from push-announcement endpoint",
                status_code=response.status_code,
            )
        body = response.json()
        return PushAnnouncementResult(recipient_count=int(body.get("recipientCount", 0)))

    async def get_operator_stats(
        self, *, directus_user_id: str, country: str
    ) -> OperatorStatsResult:
        """GET /v1/internal/telegram/operator/stats."""
        url = f"{self._base_url}{OPERATOR_STATS_PATH}"
        try:
            response = await self._client.get(
                url,
                params={"directusUserId": directus_user_id, "country": country},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"get_operator_stats request failed: {exc}") from exc
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from operator stats endpoint",
                status_code=response.status_code,
            )
        body = response.json()
        return OperatorStatsResult(
            events_managed=int(body.get("eventsManaged", 0)),
            registrations_this_period=int(body.get("registrationsThisPeriod", 0)),
        )

    # ── FR-AUTH-005 link methods ───────────────────────────────────────────────

    async def request_link_start(self, *, telegram_id: str, email: str) -> LinkStartResult:
        """Start the link flow via POST /v1/telegram/link/start.

        FR-AUTH-005 Surface B. Sends a 6-digit OTP to the supplied email
        if a member account exists for it (email enumeration is prevented
        server-side — the API always returns the same envelope shape
        regardless of whether the member exists).

        Raises:
            LinkRateLimitedError: API returned 400 rate_limited — too many
                active challenges from this Telegram ID.
            ApiUnavailableError: any other non-2xx response, network error,
                or timeout.
        """
        url = f"{self._base_url}{LINK_START_PATH}"
        try:
            response = await self._client.post(
                url,
                json={"tg_user_id": telegram_id, "email": email},
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"request_link_start request failed: {exc}") from exc

        if response.status_code == httpx.codes.BAD_REQUEST:
            error = response.json().get("message") or response.json().get("error", "")
            if "rate_limited" in str(error):
                raise LinkRateLimitedError(telegram_id)
            raise ApiUnavailableError(
                f"bad request from link/start: {error}",
                status_code=response.status_code,
            )
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from link/start endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return LinkStartResult(
            challenge_id=body["challenge_id"],
            sent_to_email_masked=body.get("sent_to_email_masked", ""),
        )

    async def request_link_confirm(
        self,
        *,
        challenge_id: str,
        code: str,
        telegram_id: str,
        telegram_username: str | None,
    ) -> LinkConfirmResult:
        """Complete the link flow via POST /v1/telegram/link/confirm.

        FR-AUTH-005 Surface B. Verifies the OTP and writes the Telegram
        identity to the member's Directus row.

        Raises:
            LinkInvalidCodeError: API returned 401 invalid_code.
            LinkMemberNotFoundError: API returned 404 member_not_found.
            LinkAlreadyLinkedOtherError: API returned 409
                already_linked_to_different_account.
            ApiUnavailableError: any other non-2xx response, network error,
                or timeout.
        """
        url = f"{self._base_url}{LINK_CONFIRM_PATH}"
        payload: dict[str, object] = {
            "challenge_id": challenge_id,
            "code": code,
            "tg_user_id": telegram_id,
        }
        if telegram_username is not None:
            payload["tg_username"] = telegram_username
        try:
            response = await self._client.post(
                url,
                json=payload,
                headers={"x-internal-auth": self._token},
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"request_link_confirm request failed: {exc}") from exc

        if response.status_code == httpx.codes.UNAUTHORIZED:
            raise LinkInvalidCodeError(challenge_id)
        if response.status_code == httpx.codes.NOT_FOUND:
            raise LinkMemberNotFoundError(challenge_id)
        if response.status_code == httpx.codes.CONFLICT:
            raise LinkAlreadyLinkedOtherError(telegram_id)
        if response.status_code != httpx.codes.OK:
            raise ApiUnavailableError(
                f"unexpected status {response.status_code} from link/confirm endpoint",
                status_code=response.status_code,
            )

        body = response.json()
        return LinkConfirmResult(
            member_id=body["member_id"],
            tenant=body.get("tenant", ""),
        )