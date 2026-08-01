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
    "help.interests": "/interests — мои темы интересов",
    "help.upgrade": "/upgrade — привязать email к аккаунту",
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
    # FEAT-BOT-2 (FR-BOT-002 PR 5/6)
    "interests.title": "<b>Мои темы интересов</b>\nНажмите на тему, чтобы добавить или убрать её.",
    "interests.unavailable": (
        "Не удалось загрузить темы интересов — сервис временно недоступен. "
        "Попробуйте ещё раз чуть позже."
    ),
    # Same 7 concepts as TelegramEventTopicsService's own
    # KNOWN_EVENT_TOPIC_TRANSLATIONS ru values (telegram-event-topics.service.ts)
    # — reused verbatim for consistency between a member's interest and an
    # event's topic tag.
    "interests.topic.llm": "Большие языковые модели",
    "interests.topic.mlops": "MLOps",
    "interests.topic.computer-vision": "Компьютерное зрение",
    "interests.topic.product": "AI-продукт",
    "interests.topic.career": "Карьера в AI",
    "interests.topic.ethics": "Этика AI",
    "interests.topic.infra": "AI-инфраструктура",
    # FEAT-BOT-2 (FR-BOT-002 PR 6/6)
    "upgrade.already_full_account": ("Этот аккаунт уже полноценный — привязывать email не нужно."),
    "upgrade.prompt_email": (
        "Введите email — мы отправим на него ссылку для входа. "
        "После перехода по ссылке ваш аккаунт станет полноценным: "
        "баллы и таблица лидеров станут доступны."
    ),
    "upgrade.invalid_email": ("Похоже, это не email. Введите адрес в формате name@example.com."),
    "upgrade.magic_link_sent": (
        "Ссылка для входа отправлена на указанный email. Она действительна "
        "около 30 минут — перейдите по ней, чтобы завершить привязку."
    ),
    "upgrade.telegram_user_not_found": (
        "Не удалось найти ваш аккаунт. Попробуйте выполнить /start ещё раз."
    ),
    "upgrade.email_already_in_use": (
        "Этот email уже используется другим аккаунтом. Введите другой адрес "
        "через /upgrade, либо войдите на сайте с этим email через ссылку для входа."
    ),
    "upgrade.unavailable": (
        "Не удалось начать привязку email — сервис временно недоступен. "
        "Попробуйте ещё раз чуть позже."
    ),
    # FEAT-BOT-3 (FR-BOT-003) — operator commands
    "operator.access_denied": "У вас нет доступа к этой команде.",
    "help.operator_section": "Команды организатора:",
    "help.attendance": "/attendance <N> — явка на мероприятие №N",
    "help.scan": "/scan — сканировать QR-код для отметки участника",
    "help.approvals": "/approvals — заявки на одобрение",
    "help.announce": "/announce <N> — рассылка участникам мероприятия №N",
    "attendance.usage": "Использование: /attendance <номер>, например /attendance 5",
    "attendance.result": (
        "<b>{title}</b>\n"
        "Зарегистрированы: {registered}\n"
        "Пришли (отмечено): {attended}\n"
        "Список ожидания: {waitlisted}"
    ),
    "scan.prompt": "Отправьте фото QR-кода для отметки участника.",
    "scan.no_photo": "Пожалуйста, отправьте фото с QR-кодом.",
    "scan.no_qr_found": "QR-код на изображении не найден. Попробуйте ещё раз с другим ракурсом.",
    "scan.not_found": "QR-код не распознан — возможно, код недействителен или устарел.",
    "scan.ineligible": "Эта регистрация не может быть отмечена (отменена или в листе ожидания).",
    "scan.success": "Участник отмечен ✓\n{member}\n{event}",
    "scan.already_checked_in": "Участник уже был отмечен ранее.\n{member}\n{event}",
    "scan.unknown_member": "Участник",
    "approvals.title": "Заявки на одобрение:",
    "approvals.item": "{member} → {event}",
    "approvals.empty": "Нет заявок на одобрение.",
    "approvals.button_approve": "Одобрить",
    "approvals.button_decline": "Отклонить",
    "approvals.approved": "Заявка одобрена.",
    "approvals.declined": "Заявка отклонена.",
    "announce.usage": "Использование: /announce <номер>, например /announce 5",
    "announce.prompt_message": (
        "Введите текст объявления. Оно будет отправлено всем подтверждённым участникам."
    ),
    "announce.empty_message": "Текст объявления не может быть пустым. Введите сообщение.",
    "announce.message_too_long": "Сообщение слишком длинное (максимум 4000 символов).",
    "announce.sent": "Объявление отправлено {count} участникам.",
    "me.operator_stats_title": "<b>Статистика организатора:</b>",
    "me.operator_stats_events": "Мероприятий в стране: {count}",
    "me.operator_stats_registrations": "Регистраций за 30 дней: {count}",
}
