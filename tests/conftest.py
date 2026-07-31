"""Shared pytest fixtures / helpers for building fake aiogram Update objects."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from aiogram.types import CallbackQuery, Chat, Message, Update, User


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


@contextmanager
def mock_edit_text(message: Message):
    """Patch Message.edit_text — same rationale as mock_answer above.

    Used by the /events pagination callback handler, which edits the
    existing message in place rather than sending a new one.
    """
    with patch.object(type(message), "edit_text", new=AsyncMock()) as mocked:
        yield mocked


@contextmanager
def mock_callback_answer(callback: CallbackQuery):
    """Patch CallbackQuery.answer — same rationale as mock_answer above."""
    with patch.object(type(callback), "answer", new=AsyncMock()) as mocked:
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


def make_callback_query(
    *,
    callback_id: str = "cb-1",
    data: str | None = None,
    telegram_user_id: int = 12345,
    message_id: int = 1,
) -> CallbackQuery:
    """Build a minimal, valid aiogram CallbackQuery with an attached Message.

    Used to test the /events pagination buttons and the /event Register
    placeholder button — both are callback_query handlers, not message
    handlers, so they need this fixture rather than make_message_update.
    """
    user = User(id=telegram_user_id, is_bot=False, first_name="Test")
    chat = Chat(id=telegram_user_id, type="private")
    message = Message(
        message_id=message_id,
        date=datetime.now(UTC),
        chat=chat,
        from_user=user,
        text="placeholder",
    )
    return CallbackQuery(
        id=callback_id,
        from_user=user,
        chat_instance="test-chat-instance",
        message=message,
        data=data,
    )
