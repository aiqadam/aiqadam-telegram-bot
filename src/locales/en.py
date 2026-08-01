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
    "help.upgrade": "/upgrade — link an email to your account",
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
    # FEAT-BOT-2 (FR-BOT-002 PR 6/6)
    "upgrade.already_full_account": "This account is already a full member — no email needed.",
    "upgrade.prompt_email": (
        "Enter your email — we'll send you a sign-in link. Once you click it, "
        "your account becomes a full member: points and the leaderboard unlock."
    ),
    "upgrade.invalid_email": (
        "That doesn't look like an email. Enter an address like name@example.com."
    ),
    "upgrade.magic_link_sent": (
        "A sign-in link was sent to that email. It's valid for about 30 minutes — "
        "click it to finish linking your account."
    ),
    "upgrade.telegram_user_not_found": "Couldn't find your account. Try running /start again.",
    "upgrade.email_already_in_use": (
        "That email is already used by another account. Enter a different address "
        "via /upgrade, or sign in on the web with that email using its sign-in link."
    ),
    "upgrade.unavailable": (
        "Couldn't start linking your email — the service is temporarily unavailable. "
        "Please try again shortly."
    ),
    # FEAT-BOT-3 (FR-BOT-003) — operator commands
    "operator.access_denied": "You don't have access to this command.",
    "help.operator_section": "Organizer commands:",
    "help.attendance": "/attendance <N> — live attendance for event #N",
    "help.scan": "/scan — scan a member's QR code to check them in",
    "help.approvals": "/approvals — pending registration approvals",
    "help.announce": "/announce <N> — push announcement to event #N registrants",
    "attendance.usage": "Usage: /attendance <number>, e.g. /attendance 5",
    "attendance.result": (
        "<b>{title}</b>\n"
        "Registered: {registered}\n"
        "Checked in: {attended}\n"
        "Waitlisted: {waitlisted}"
    ),
    "scan.prompt": "Send the QR code photo to check in a member.",
    "scan.no_photo": "Please send a photo with a QR code.",
    "scan.no_qr_found": "No QR code found in the image. Try again with a clearer photo.",
    "scan.not_found": "QR code not recognised — it may be invalid or expired.",
    "scan.ineligible": "This registration can't be checked in (cancelled or waitlisted).",
    "scan.success": "Checked in ✓\n{member}\n{event}",
    "scan.already_checked_in": "Already checked in earlier.\n{member}\n{event}",
    "scan.unknown_member": "Member",
    "approvals.title": "Pending approvals:",
    "approvals.item": "{member} → {event}",
    "approvals.empty": "No pending approvals.",
    "approvals.button_approve": "Approve",
    "approvals.button_decline": "Decline",
    "approvals.approved": "Approved.",
    "approvals.declined": "Declined.",
    "announce.usage": "Usage: /announce <number>, e.g. /announce 5",
    "announce.prompt_message": (
        "Enter your announcement text. It will be sent to all confirmed registrants."
    ),
    "announce.empty_message": "Announcement text cannot be empty. Please enter a message.",
    "announce.message_too_long": "Message too long (maximum 4000 characters).",
    "announce.sent": "Announcement sent to {count} members.",
    "me.operator_stats_title": "<b>Organizer stats:</b>",
    "me.operator_stats_events": "Events in your country: {count}",
    "me.operator_stats_registrations": "Registrations (last 30 days): {count}",
}
