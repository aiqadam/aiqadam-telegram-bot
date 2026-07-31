"""Local SQLite cache: telegram_id -> directusUserId.

FR-BOT-001 §2: "Bot stores ONLY (telegram_id -> directusUserId) in a local
SQLite for fast lookup on every command. No other state." This cache is
bot-local, disposable, and rebuildable at any time from the API's lookup
endpoint (ADR-0034 §Q3 — the bot owns no business state; this is purely a
performance cache, never a source of truth).

Uses the stdlib `sqlite3` module synchronously — cache reads/writes are
single-row key lookups, fast enough not to need an async driver, and
keeping this dependency-free matches the thin-bot framing.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS telegram_user_cache (
    telegram_id TEXT PRIMARY KEY,
    directus_user_id TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
"""


class UserCache:
    """Thin synchronous wrapper around a single SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def get(self, telegram_id: str) -> str | None:
        """Return the cached directusUserId for telegram_id, or None if unknown."""
        row = self._conn.execute(
            "SELECT directus_user_id FROM telegram_user_cache WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        return row[0] if row else None

    def set(self, telegram_id: str, directus_user_id: str | None) -> None:
        """Upsert the cached mapping for telegram_id."""
        self._conn.execute(
            """
            INSERT INTO telegram_user_cache (telegram_id, directus_user_id)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                directus_user_id = excluded.directus_user_id,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            """,
            (telegram_id, directus_user_id),
        )
        self._conn.commit()
