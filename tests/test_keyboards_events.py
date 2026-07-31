"""Tests for src/keyboards/events.py (FR-BOT-002 PR 1/6)."""

from __future__ import annotations

from src.keyboards.events import event_detail_keyboard, events_page_keyboard
from src.locales import t


def test_events_page_keyboard_returns_none_for_a_single_page() -> None:
    assert events_page_keyboard(offset=0, limit=5, total=3) is None


def test_events_page_keyboard_shows_only_next_on_first_page() -> None:
    keyboard = events_page_keyboard(offset=0, limit=5, total=12)
    assert keyboard is not None
    texts = [b.text for row in keyboard.inline_keyboard for b in row]
    assert texts == [t("events.button_next")]


def test_events_page_keyboard_shows_both_buttons_on_a_middle_page() -> None:
    keyboard = events_page_keyboard(offset=5, limit=5, total=12)
    assert keyboard is not None
    texts = [b.text for row in keyboard.inline_keyboard for b in row]
    assert texts == [t("events.button_prev"), t("events.button_next")]


def test_events_page_keyboard_shows_only_prev_on_last_page() -> None:
    keyboard = events_page_keyboard(offset=10, limit=5, total=12)
    assert keyboard is not None
    texts = [b.text for row in keyboard.inline_keyboard for b in row]
    assert texts == [t("events.button_prev")]


def test_events_page_keyboard_next_callback_data_advances_by_limit() -> None:
    keyboard = events_page_keyboard(offset=0, limit=5, total=12)
    assert keyboard is not None
    next_button = keyboard.inline_keyboard[0][0]
    assert next_button.callback_data == "evpg:5"


def test_events_page_keyboard_prev_callback_data_never_goes_negative() -> None:
    keyboard = events_page_keyboard(offset=3, limit=5, total=12)
    assert keyboard is not None
    prev_button = keyboard.inline_keyboard[0][0]
    assert prev_button.callback_data == "evpg:0"


def test_event_detail_keyboard_shows_register_label_when_not_registered() -> None:
    keyboard = event_detail_keyboard(event_id="evt-1", is_registered=False)
    button = keyboard.inline_keyboard[0][0]
    assert button.text == t("event.button_register")
    assert button.callback_data == "evreg:evt-1"


def test_event_detail_keyboard_shows_going_label_when_registered() -> None:
    keyboard = event_detail_keyboard(event_id="evt-1", is_registered=True)
    button = keyboard.inline_keyboard[0][0]
    assert button.text == t("event.button_going")
