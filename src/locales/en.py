"""English (secondary) locale strings."""

STRINGS: dict[str, str] = {
    "start.welcome": (
        "Welcome to AI Qadam! I'll help you keep up with community events. "
        "Full registration is coming soon — in the meantime, try /help."
    ),
    "unknown_command": "I don't know that command — try /help.",
    "error.generic": "Something went wrong. We've logged it — please try again shortly.",
    # FEAT-BOT-2 (FR-BOT-002 PR 1/6)
    "help.title": "Available commands:",
    "help.start": "/start — welcome message and country selection",
    "help.events": "/events — list upcoming events",
    "help.event": "/event <N> — details for event #N",
    "help.register": "/register <N> — register for event #N",
    "help.cancel": "/cancel <N> — cancel registration for event #N",
    "help.me": "/me — my registrations and account status",
    "help.leaderboard": "/leaderboard — leaderboard",
    "help.interests": "/interests — my topic interests",
    "help.upgrade": "/upgrade — link an email to your account (coming soon)",
    "help.help": "/help — this message",
    "events.empty": "No upcoming events yet. Check back soon!",
    "events.title": "Upcoming events:",
    "events.item": "{title} — {date} (registered: {count})\n/event {id}",
    "events.page_info": "Page {page} of {total_pages}",
    "events.button_next": "Next ➡️",
    "events.button_prev": "⬅️ Previous",
    "events.button_detail": "Details",
    "events.unavailable": (
        "Couldn't load events — the service is temporarily unavailable. Please try again shortly."
    ),
    "events.usage": "Usage: /event <number>, e.g. /event 5",
    "event.not_found": "Event not found — it may have already happened or been cancelled.",
    "event.unavailable": (
        "Couldn't load the event — the service is temporarily unavailable. "
        "Please try again shortly."
    ),
    "event.detail": (
        "<b>{title}</b>\n"
        "🗓 {date}\n"
        "{venue_line}"
        "👥 Registered: {registered}{capacity_line}\n\n"
        "{description}"
    ),
    "event.venue_line": "📍 {venue}\n",
    "event.capacity_line": " / {capacity}",
    "event.button_register": "Register",
    "event.button_going": "✅ You're going",
    # FEAT-BOT-2 (FR-BOT-002 PR 2/6)
    "register.usage": "Usage: /register <number>, e.g. /register 5",
    "register.confirmed": 'You\'re registered for "{title}"! See you there.',
    "register.waitlisted": (
        '"{title}" is full — you\'ve been added to the waitlist. '
        "We'll let you know if a spot opens up."
    ),
    "register.consent_required": (
        "This event requires additional confirmation — please finish registering on aiqadam.org."
    ),
    "register.ineligible": "Couldn't complete registration — try running /start again.",
    "cancel.usage": "Usage: /cancel <number>, e.g. /cancel 5",
    "cancel.confirmed": "Registration cancelled.",
    "cancel.not_registered": "You weren't registered for this event.",
    # FEAT-BOT-2 (FR-BOT-002 PR 3/6)
    "me.unavailable": (
        "Couldn't load your profile — the service is temporarily unavailable. "
        "Please try again shortly."
    ),
    "me.title": "<b>Your profile</b>",
    "me.registrations_title": "My registrations:",
    "me.registrations_empty": "No active registrations yet. Check out /events!",
    "me.registration_item": "{status_badge} {title} — {date}",
    "me.status_registered": "[REGISTERED]",
    "me.status_waitlisted": "[WAITLISTED]",
    "me.status_attended": "[ATTENDED]",
    "me.points_total": "Points: {points}",
    "me.temp_account_nudge": (
        "This is a temporary account — link an email via /upgrade so you don't "
        "lose your registration history and points."
    ),
    "me.link_web_cta": "Link your account on the web: use /upgrade.",
    "me.button_cancel": "Cancel registration",
    # FEAT-BOT-2 (FR-BOT-002 PR 4/6)
    "leaderboard.title": "<b>Leaderboard</b>",
    "leaderboard.empty": "No members with points in your country yet.",
    "leaderboard.item": "{rank}. {name} — {points}",
    "leaderboard.item_caller": "<b>{rank}. {name} — {points} (you)</b>",
    "leaderboard.unavailable": (
        "Couldn't load the leaderboard — the service is temporarily unavailable. "
        "Please try again shortly."
    ),
    # FEAT-BOT-2 (FR-BOT-002 PR 5/6)
    "interests.title": "<b>My topic interests</b>\nTap a topic to add or remove it.",
    "interests.unavailable": (
        "Couldn't load your topic interests — the service is temporarily unavailable. "
        "Please try again shortly."
    ),
    # Same 7 concepts as TelegramEventTopicsService's own KNOWN_EVENT_TOPICS
    # english `label` values (telegram-event-topics.service.ts) — reused
    # verbatim for consistency between a member's interest and an event's
    # topic tag.
    "interests.topic.llm": "Large Language Models",
    "interests.topic.mlops": "MLOps",
    "interests.topic.computer-vision": "Computer Vision",
    "interests.topic.product": "AI Product",
    "interests.topic.career": "AI Careers",
    "interests.topic.ethics": "AI Ethics",
    "interests.topic.infra": "AI Infrastructure",
}
