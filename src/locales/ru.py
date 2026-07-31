"""Russian (primary) locale strings."""

STRINGS: dict[str, str] = {
    "start.welcome": (
        "Здравствуйте! Добро пожаловать в AI Qadam. "
        "Я помогу вам следить за мероприятиями сообщества. "
        "Полная регистрация скоро будет доступна — а пока попробуйте /help."
    ),
    "unknown_command": "Я не знаю эту команду — попробуйте /help.",
    "error.generic": "Что-то пошло не так. Мы уже разбираемся. Попробуйте ещё раз чуть позже.",
    # FEAT-BOT-2 (FR-BOT-002 PR 1/6)
    "help.title": "Доступные команды:",
    "help.start": "/start — приветствие и выбор страны",
    "help.events": "/events — список ближайших мероприятий",
    "help.event": "/event <N> — подробности о мероприятии №N",
    "help.register": "/register <N> — запись на мероприятие №N",
    "help.cancel": "/cancel <N> — отмена записи на мероприятие №N",
    "help.me": "/me — мои записи и статус аккаунта",
    "help.leaderboard": "/leaderboard — таблица лидеров",
    "help.interests": "/interests — мои темы интересов (скоро)",
    "help.upgrade": "/upgrade — привязать email к аккаунту (скоро)",
    "help.help": "/help — это сообщение",
    "events.empty": "Пока нет ближайших мероприятий. Загляните позже!",
    "events.title": "Ближайшие мероприятия:",
    "events.item": "{title} — {date} (записано: {count})\n/event {id}",
    "events.page_info": "Страница {page} из {total_pages}",
    "events.button_next": "Далее ➡️",
    "events.button_prev": "⬅️ Назад",
    "events.button_detail": "Подробнее",
    "events.unavailable": (
        "Не удалось загрузить мероприятия — сервис временно недоступен. "
        "Попробуйте ещё раз чуть позже."
    ),
    "events.usage": "Использование: /event <номер>, например /event 5",
    "event.not_found": "Мероприятие не найдено — возможно, оно уже прошло или было отменено.",
    "event.unavailable": (
        "Не удалось загрузить мероприятие — сервис временно недоступен. "
        "Попробуйте ещё раз чуть позже."
    ),
    "event.detail": (
        "<b>{title}</b>\n"
        "🗓 {date}\n"
        "{venue_line}"
        "👥 Записано: {registered}{capacity_line}\n\n"
        "{description}"
    ),
    "event.venue_line": "📍 {venue}\n",
    "event.capacity_line": " / {capacity}",
    "event.button_register": "Зарегистрироваться",
    "event.button_going": "✅ Вы записаны",
    # FEAT-BOT-2 (FR-BOT-002 PR 2/6)
    "register.usage": "Использование: /register <номер>, например /register 5",
    "register.confirmed": "Вы зарегистрированы на «{title}»! Ждём вас там.",
    "register.waitlisted": (
        "Мероприятие «{title}» уже заполнено — вы добавлены в список ожидания. "
        "Мы сообщим, если освободится место."
    ),
    "register.consent_required": (
        "Это мероприятие требует дополнительного согласия — завершите регистрацию "
        "на сайте aiqadam.org."
    ),
    "register.ineligible": (
        "Не удалось завершить регистрацию — попробуйте выполнить /start ещё раз."
    ),
    "cancel.usage": "Использование: /cancel <номер>, например /cancel 5",
    "cancel.confirmed": "Регистрация отменена.",
    "cancel.not_registered": "Вы не были записаны на это мероприятие.",
    # FEAT-BOT-2 (FR-BOT-002 PR 3/6)
    "me.unavailable": (
        "Не удалось загрузить профиль — сервис временно недоступен. Попробуйте ещё раз чуть позже."
    ),
    "me.title": "<b>Ваш профиль</b>",
    "me.registrations_title": "Мои записи:",
    "me.registrations_empty": "Пока нет активных записей. Посмотрите /events!",
    "me.registration_item": "{status_badge} {title} — {date}",
    "me.status_registered": "[ЗАПИСАН]",
    "me.status_waitlisted": "[ЛИСТ ОЖИДАНИЯ]",
    "me.status_attended": "[ПОСЕТИЛ]",
    "me.points_total": "Баллы: {points}",
    "me.temp_account_nudge": (
        "Это временный аккаунт — привяжите email через /upgrade, чтобы не потерять "
        "историю записей и баллы."
    ),
    "me.link_web_cta": "Привязать аккаунт на сайте: используйте /upgrade.",
    "me.button_cancel": "Отменить запись",
    # FEAT-BOT-2 (FR-BOT-002 PR 4/6)
    "leaderboard.title": "<b>Таблица лидеров</b>",
    "leaderboard.empty": "Пока нет участников с баллами в вашей стране.",
    "leaderboard.item": "{rank}. {name} — {points}",
    "leaderboard.item_caller": "<b>{rank}. {name} — {points} (вы)</b>",
    "leaderboard.unavailable": (
        "Не удалось загрузить таблицу лидеров — сервис временно недоступен. "
        "Попробуйте ещё раз чуть позже."
    ),
}
