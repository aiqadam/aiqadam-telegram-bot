# aiqadam-telegram-bot

Telegram bot + outbound notifier for [AI Qadam](https://github.com/aiqadam/ai-qadam-platform).

Two processes, one bot token, one bot account (`@aiqadam_bot`):

- **`bot`** — aiogram long-poll client. Inbound only: `/start`, `/events`,
  `/link`, registration FSM, QR check-in, `/stop`.
- **`notifier`** — Redis Streams consumer (`tg.dispatch.v1`). Outbound only:
  sends DMs and channel posts published by the API's outbox relay.

The bot owns no business state — no Postgres, no member graph, no
templates. All of that is canonical in the `aiqadam` monorepo (Directus +
NestJS) per [ADR-0033](https://github.com/aiqadam/ai-qadam-platform/blob/main/docs/adr/0033-community-member-graph.md).

Full design decisions: [ADR-0034](https://github.com/aiqadam/ai-qadam-platform/blob/main/docs/adr/0034-telegram-bot-and-sender.md)
in the main repo.

This repo is vendored into the main repo as a git submodule at `apps/bot/`
so a single VS Code workspace and the same agent fleet can manage both
projects, while keeping independent deploy/CI/Coolify boundaries and
language separation (Python here, TypeScript/pnpm there).

## Status

Inbound scaffold implemented (FR-BOT-001 / FEAT-BOT-1): `/start` smoke-test
handler, unknown-command fallback, and the full middleware stack
(rate-limit, auth, tenant, structured logging). The `notifier` process and
the full member/operator command set (`/events`, `/link`, registration
FSM, QR check-in, `/stop`) are not yet built — tracked as FR-BOT-002,
FR-BOT-003, and FR-NTF-004 in the main repo's requirements registry.

## Development

```bash
uv sync                      # or: python -m venv .venv && pip install -e ".[dev]"
cp .env.example .env         # fill in TELEGRAM_BOT_TOKEN, INTERNAL_API_URL, INTERNAL_API_TOKEN
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python -m src.main    # start long-polling
```

## Project structure

```
src/
├── handlers/       # command and callback handlers (/start, unknown-command fallback)
├── services/       # API client (calls the internal lookup endpoint), SQLite cache
├── middlewares/    # rate-limit, auth, tenant, structured logging
├── keyboards/      # inline keyboard builders (stub — no interactive keyboards yet)
├── states/         # aiogram FSM states (stub — no multi-step flows yet)
├── locales/        # i18n strings (ru primary, en secondary)
├── config.py       # typed settings — thin-bot guarantee lives here
├── logging_setup.py
├── error_handler.py
└── main.py
```

## Thin-bot guarantee

This bot never holds `DIRECTUS_TOKEN`, `AUTHENTIK_API_TOKEN`, or
`TWENTY_API_TOKEN` — every integration beyond Telegram itself goes through
the NestJS API using `INTERNAL_API_TOKEN`. Enforced by
`tests/test_thin_bot_guarantee.py`.
