from serpapi_challenge26 import i18n


def test_lang_from_locale_prefix():
    assert i18n._lang_from_locale("Portuguese_Brazil.1252") == "pt"
    assert i18n._lang_from_locale("pt_BR") == "pt"
    assert i18n._lang_from_locale("en_US") == "en"
    assert i18n._lang_from_locale("C") == "en"
    assert i18n._lang_from_locale(None) == "en"


def test_format_int_strips_grouping_for_en():
    i18n._user_locale_set = False
    import locale

    locale.setlocale(locale.LC_ALL, "C")
    formatted = i18n.format_int(1355)
    assert formatted in ("1355", "1,355", "1.355")


def test_format_percent_shape():
    i18n._user_locale_set = False
    import locale

    locale.setlocale(locale.LC_ALL, "C")
    assert i18n.format_percent(0.15) == "15%"


def test_format_decimal_whole_number():
    i18n._user_locale_set = False
    import locale

    locale.setlocale(locale.LC_ALL, "C")
    assert i18n.format_decimal(2018.0) == "2018"
    assert i18n.format_decimal(2018.8) == "2018.8"


def test_set_user_locale_tolerates_invalid_locale(monkeypatch):
    i18n._user_locale_set = False
    import locale

    def _boom(category, value):
        raise locale.Error("bad locale")

    monkeypatch.setattr(locale, "setlocale", _boom)
    i18n.set_user_locale()  # must not raise
    assert i18n._user_locale_set is True


def test_set_user_locale_runs_once(monkeypatch):
    i18n._user_locale_set = False
    calls = []
    import locale

    real_setlocale = locale.setlocale

    def _tracking(category, value):
        calls.append(value)
        return real_setlocale(category, value)

    monkeypatch.setattr(locale, "setlocale", _tracking)
    i18n.set_user_locale()
    i18n.set_user_locale()
    assert len(calls) == 1
    i18n._user_locale_set = False


def test_set_language_pt_loads_translation():
    i18n.set_language("pt")
    assert i18n._("Research topic") != "Research topic"


def test_set_language_en_uses_null_translations():
    i18n.set_language("en")
    assert i18n._("Research topic") == "Research topic"


def test_set_language_unknown_falls_back_to_null():
    i18n.set_language("fr")
    assert i18n._("Research topic") == "Research topic"


def test_set_language_pt_missing_catalog_falls_back_to_null(monkeypatch):
    # Force the translation lookup to fail and cover the OSError fallback branch.
    import gettext

    def _boom(*args, **kwargs):
        raise OSError("missing catalog")

    monkeypatch.setattr(gettext, "translation", _boom)
    i18n.set_language("pt")
    assert i18n._("Research topic") == "Research topic"
