"""Structured JSON logging to stdout, for Loki ingestion (FR-BOT-001 §5).

No external logging library is added — Python's stdlib `logging` module
with a small JSON formatter is enough for this scaffold's needs and keeps
the dependency surface minimal, per FR-BOT-001's "thin bot" framing.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

_RESERVED_LOG_RECORD_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)


class JsonFormatter(logging.Formatter):
    """Formats each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include any structured `extra=` fields the caller attached (e.g.
        # telegram_id, command, duration_ms, status) without hardcoding
        # their names here — every log call site owns its own fields.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_KEYS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["traceback"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger to emit one JSON line per record to stdout."""
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # aiogram's own loggers are noisy at DEBUG; let them inherit the root
    # level and handler rather than configuring separately.
    logging.getLogger("aiogram").setLevel(level.upper())
