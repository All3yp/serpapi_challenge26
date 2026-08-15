"""Tests for the Babel-compiled message catalog (plurals + compile wrapper)."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def test_compiled_catalog_has_pt_plurals():
    import gettext

    catalog = gettext.translation("messages", str(_ROOT / "locale"), languages=["pt"])
    assert catalog.ngettext("paper", "papers", 1) == "paper"
    assert catalog.ngettext("paper", "papers", 5) == "papers"
    assert catalog.ngettext("citation", "citations", 1) == "citação"
    assert catalog.ngettext("citation", "citations", 5) == "citações"


def test_compile_script_reproduces_mo(tmp_path):
    import shutil

    from compile_messages import main

    # Copy the catalog into an isolated temp dir so the test never writes to repo.
    tmp_locale = tmp_path / "locale"
    shutil.copytree(_ROOT / "locale", tmp_locale)

    main(tmp_locale)

    import gettext

    catalog = gettext.translation("messages", str(tmp_locale), languages=["pt"])
    assert catalog.ngettext("paper", "papers", 2) == "papers"
