"""i18n strings — ru primary, en secondary (FR-BOT-001 §4).

Deliberately minimal for FEAT-BOT-1: only the /start welcome message and
the unknown-command fallback need translated strings at this stage. More
locale keys will be added alongside each future handler (FR-BOT-002/003).

Usage: `from src.locales import t; t("start.welcome", lang="ru")`.
"""

from __future__ import annotations

from src.locales import en, ru

DEFAULT_LANG = "ru"

_CATALOGS: dict[str, dict[str, str]] = {
    "ru": ru.STRINGS,
    "en": en.STRINGS,
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Look up a locale string by key, falling back ru -> en -> the key itself."""
    catalog = _CATALOGS.get(lang, _CATALOGS[DEFAULT_LANG])
    if key in catalog:
        return catalog[key]

    # Fall back to the default catalog if the requested language is missing
    # this specific key (e.g. a key added to `en` but not yet translated).
    fallback = _CATALOGS[DEFAULT_LANG]
    return fallback.get(key, key)
