import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from compile_messages import compile_mo, parse_po  # noqa: E402


def test_mo_roundtrip_is_parseable_by_gettext(tmp_path):
    po_text = '''msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "hello"
msgstr "olá"

msgid "world"
msgstr "mundo"
'''
    entries = parse_po(po_text)
    assert entries[0][0] == ""

    mo_path = tmp_path / "messages.mo"
    mo_path.write_bytes(compile_mo(entries))

    import gettext

    with mo_path.open("rb") as fp:
        catalog = gettext.GNUTranslations(fp)
    assert catalog.gettext("hello") == "olá"
    assert catalog.gettext("world") == "mundo"
