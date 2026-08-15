"""Locale detection, number formatting, and gettext translation."""

from __future__ import annotations

import gettext
import locale as _locale
from pathlib import Path

_DOMAIN = "messages"
_LOCALE_DIR = Path(__file__).resolve().parents[2] / "locale"

_user_locale_set = False
_translator = gettext.NullTranslations()


def set_user_locale() -> None:
    global _user_locale_set
    if _user_locale_set:
        return
    try:
        _locale.setlocale(_locale.LC_ALL, "")
    except _locale.Error:
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
    current, _ = _locale.getlocale(_locale.LC_CTYPE)
    return _lang_from_locale(current)


def set_language(lang: str) -> None:
    global _translator
    if lang != "pt":
        _translator = gettext.NullTranslations()
        return
    try:
        _translator = gettext.translation(_DOMAIN, _LOCALE_DIR, languages=["pt"], fallback=False)
    except (FileNotFoundError, OSError):
        _translator = gettext.NullTranslations()


def translate(message: str) -> str:
    return _translator.gettext(message)


_ = translate


def format_int(value: int) -> str:
    set_user_locale()
    return _locale.format_string("%d", value, grouping=True)


def format_percent(ratio: float) -> str:
    set_user_locale()
    return _locale.format_string("%.0f%%", ratio * 100, grouping=True)


def format_decimal(value: float, *, grouping: bool = False) -> str:
    set_user_locale()
    if value == int(value):
        return _locale.format_string("%d", int(value), grouping=grouping)
    return _locale.format_string("%.1f", value, grouping=grouping)
