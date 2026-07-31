"""Shared pytest fixtures / helpers for building fake aiogram Update objects."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from aiogram.types import Chat, Message, Update, User


@contextmanager
def mock_answer(message: Message):
    """Patch Message.answer for the duration of the `with` block.

    aiogram's Message is a frozen pydantic model, so `message.answer = ...`
    raises a ValidationError. Patching the bound method on the class
    (scoped to this instance via autospec=False) is the supported way to
    intercept outgoing replies in tests without a live Bot/session.
    """
    with patch.object(type(message), "answer", new=AsyncMock()) as mocked:
        yield mocked


def make_message_update(
    *,
    update_id: int = 1,
    text: str = "/start",
    telegram_user_id: int = 12345,
    message_id: int = 1,
) -> Update:
    """Build a minimal, valid aiogram Update wrapping a text Message."""
    user = User(id=telegram_user_id, is_bot=False, first_name="Test")
    chat = Chat(id=telegram_user_id, type="private")
    message = Message(
        message_id=message_id,
        date=datetime.now(UTC),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=update_id, message=message)
