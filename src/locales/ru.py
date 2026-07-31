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
    "help.register": "/register <N> — запись на мероприятие №N (скоро)",
    "help.cancel": "/cancel <N> — отмена записи на мероприятие №N (скоро)",
    "help.me": "/me — мои записи и статус аккаунта (скоро)",
    "help.leaderboard": "/leaderboard — таблица лидеров (скоро)",
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
    "event.register_placeholder": (
        "Регистрация появится в одном из следующих обновлений бота. Совсем скоро!"
    ),
}
