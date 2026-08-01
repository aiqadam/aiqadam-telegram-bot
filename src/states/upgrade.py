"""FSM states for `/upgrade` (FR-BOT-002 PR 6/6).

The first real content in the `states/` package — `__init__.py` was a
stub reserving this package for exactly this kind of multi-step flow (see
its own docstring). `/upgrade` is a single-step conversation: prompt for an
email address, then handle exactly one reply. One state is enough — there
is no branching sub-flow (unlike a hypothetical `/start` country-then-
interest wizard) — so this is a one-member `StatesGroup`, not a sequence.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class UpgradeStates(StatesGroup):
    awaiting_email = State()
