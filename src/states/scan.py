"""FSM states for `/scan` (FR-BOT-003)."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ScanStates(StatesGroup):
    awaiting_qr_photo = State()
