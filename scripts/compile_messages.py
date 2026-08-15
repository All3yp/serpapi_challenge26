"""Compile ``.po`` catalogs to ``.mo`` with Babel.

Thin wrapper around ``babel.messages.mofile.write_mo`` so the build stays
invocable as ``uv run python scripts/compile_messages.py``. The ``.mo`` files
are generated artifacts — regenerate them whenever ``messages.po`` changes:

    uv run pybabel compile -D messages -d locale
"""
from __future__ import annotations

from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

_LOCALE_DIR = Path(__file__).resolve().parents[1] / "locale"


def main(locale_dir: Path | str = _LOCALE_DIR) -> None:
    root = Path(locale_dir)
    compiled = 0
    for po_path in sorted(root.glob("*/LC_MESSAGES/*.po")):
        with po_path.open(encoding="utf-8") as fp:
            catalog = read_po(fp)
        mo_path = po_path.with_suffix(".mo")
        with mo_path.open("wb") as fp:
            write_mo(fp, catalog)
        compiled += 1
        print(f"compiled {mo_path} ({len(catalog)} strings)")
    print(f"done: {compiled} catalog(s)")


if __name__ == "__main__":
    main()
