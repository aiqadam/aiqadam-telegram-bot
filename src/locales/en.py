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
    "help.register": "/register <N> — register for event #N (coming soon)",
    "help.cancel": "/cancel <N> — cancel registration for event #N (coming soon)",
    "help.me": "/me — my registrations and account status (coming soon)",
    "help.leaderboard": "/leaderboard — leaderboard (coming soon)",
    "help.interests": "/interests — my topic interests (coming soon)",
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
    "event.register_placeholder": (
        "Registration is landing in an upcoming bot update. Coming very soon!"
    ),
}
