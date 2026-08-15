"""Locale detection and number formatting via the ``locale`` module."""

from __future__ import annotations

import locale

_user_locale_set = False


def set_user_locale() -> None:
    global _user_locale_set
    if _user_locale_set:
        return
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    _user_locale_set = True


def _lang_from_locale(name: str | None) -> str:
    if not name:
        return "en"
    lowered = name.lower()
    if lowered.startswith("pt") or "portug" in lowered:
        return "pt"
    return "en"


def detect_lang() -> str:
    set_user_locale()
    current, _ = locale.getlocale(locale.LC_CTYPE)
    return _lang_from_locale(current)


def format_int(value: int) -> str:
    set_user_locale()
    return locale.format_string("%d", value, grouping=True)


def format_percent(ratio: float) -> str:
    set_user_locale()
    return locale.format_string("%.0f%%", ratio * 100, grouping=True)


def format_decimal(value: float, *, grouping: bool = False) -> str:
    set_user_locale()
    if value == int(value):
        return locale.format_string("%d", int(value), grouping=grouping)
    return locale.format_string("%.1f", value, grouping=grouping)
