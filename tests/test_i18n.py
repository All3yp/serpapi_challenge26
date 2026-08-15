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
