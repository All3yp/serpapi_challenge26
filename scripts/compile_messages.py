"""Compile ``.po`` catalogs to ``.mo`` binaries without third-party tools.

The ``.mo`` format is two (length, offset) tables plus the NUL-terminated
strings, all little-endian. ``msgfmt``/Babel are not required.
"""

from __future__ import annotations

import struct
from pathlib import Path

_MAGIC = 0x950412DE
_HEADER_FIELDS = 7
_HEADER_SIZE = _HEADER_FIELDS * 4

_ESCAPES = {
    "n": "\n",
    "t": "\t",
    '"': '"',
    "\\": "\\",
}


def _unescape(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        out.append(char)
        i += 1
    return "".join(out)


def _unquote(raw: str) -> str:
    text = raw.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return _unescape(text)


def parse_po(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    msgid: str | None = None
    msgstr: str | None = None
    current = ""

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid "):
            if msgid is not None:
                entries.append((msgid, msgstr or ""))
            msgid = _unquote(line[len("msgid "):])
            msgstr = None
            current = "msgid"
        elif line.startswith("msgstr "):
            msgstr = _unquote(line[len("msgstr "):])
            current = "msgstr"
        elif line.startswith('"'):
            if current == "msgid":
                msgid = (msgid or "") + _unquote(line)
            elif current == "msgstr":
                msgstr = (msgstr or "") + _unquote(line)

    if msgid is not None:
        entries.append((msgid, msgstr or ""))
    return entries


def compile_mo(entries: list[tuple[str, str]]) -> bytes:
    entries = sorted(set(entries), key=lambda entry: entry[0].encode("utf-8"))
    ids = [entry[0].encode("utf-8") for entry in entries]
    strs = [entry[1].encode("utf-8") for entry in entries]
    count = len(entries)

    table_size = count * 8
    data_start = _HEADER_SIZE + 2 * table_size

    original = b""
    translated = b""
    original_table: list[tuple[int, int]] = []
    translated_table: list[tuple[int, int]] = []

    original_lengths = [len(msgid_bytes) + 1 for msgid_bytes in ids]
    total_original = sum(original_lengths)

    original_offset = data_start
    for msgid_bytes in ids:
        original_table.append((len(msgid_bytes), original_offset))
        original += msgid_bytes + b"\x00"
        original_offset += len(msgid_bytes) + 1

    translated_offset = data_start + total_original
    for msgstr_bytes in strs:
        translated_table.append((len(msgstr_bytes), translated_offset))
        translated += msgstr_bytes + b"\x00"
        translated_offset += len(msgstr_bytes) + 1

    header = struct.pack(
        "<7I",
        _MAGIC,
        0,
        count,
        _HEADER_SIZE,
        _HEADER_SIZE + table_size,
        0,
        0,
    )
    body = header
    for length, offset in original_table:
        body += struct.pack("<2I", length, offset)
    for length, offset in translated_table:
        body += struct.pack("<2I", length, offset)
    body += original + translated
    return body


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    locale_dir = root / "locale"
    compiled = 0
    for po_path in sorted(locale_dir.glob("*/LC_MESSAGES/*.po")):
        entries = parse_po(po_path.read_text(encoding="utf-8"))
        mo_path = po_path.with_suffix(".mo")
        mo_path.write_bytes(compile_mo(entries))
        compiled += 1
        print(f"compiled {mo_path.relative_to(root)} ({len(entries)} strings)")
    print(f"done: {compiled} catalog(s)")


if __name__ == "__main__":
    main()
