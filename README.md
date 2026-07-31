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

Scaffold only — implementation not yet started. Tracked as FR-BOT-001 in
the main repo's requirements registry.
