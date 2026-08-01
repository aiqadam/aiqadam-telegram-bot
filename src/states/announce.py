"""FSM states for `/announce <event_id>` (FR-BOT-003)."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AnnounceStates(StatesGroup):
    awaiting_message = State()
    awaiting_confirm = State()
