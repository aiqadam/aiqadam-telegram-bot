"""FSM states for `/link` (FR-AUTH-005).

Two-step flow: prompt for email → call link/start → prompt for 6-digit
code → call link/confirm. Mirrors the `UpgradeStates` pattern from
states/upgrade.py (one extra state because the link flow has two
collection steps instead of one).
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class LinkStates(StatesGroup):
    awaiting_email = State()
    awaiting_code = State()
