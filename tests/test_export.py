"""Tests for reading-list export (export.py)."""

from gap_finder.export import (
    export_filename,
    reading_list_bib,
    reading_list_csv,
    reading_list_txt,
)
from gap_finder.scholar import Paper


def _papers():
    return [
        Paper(
            title="Explainable AI in healthcare",
            year=2023,
            authors=["Silva, João", "Maria Santos"],
            venue="Journal of AI",
            cited_by=120,
            link="https://example.org/1",
        ),
        Paper(
            title="Deep learning for vision",
            year=2020,
            authors=["Ana Souza"],
            venue="CVPR",
            cited_by=45,
            link="",
        ),
    ]


def test_csv_has_header_and_rows():
    csv_text = reading_list_csv(_papers())
    lines = csv_text.strip().splitlines()
    assert lines[0] == "title,authors,year,venue,cited_by,link"
    assert len(lines) == 3  # header + 2 papers
    assert "Explainable AI in healthcare" in lines[1]
    assert "Silva, João; Maria Santos" in lines[1]


def test_bib_contains_two_articles():
    bib = reading_list_bib(_papers())
    assert bib.count("@article{") == 2
    assert "title = {Explainable AI in healthcare}" in bib


def test_txt_respects_style():
    txt = reading_list_txt(_papers(), "ABNT")
    assert txt.count("\n\n") == 1  # two citations separated by a blank line


def test_export_filename_slugifies():
    assert export_filename("Explainable Artificial Intelligence", "bib") == \
        "explainable_artificial_intelligence.bib"
    assert export_filename("  Hello, World!!  ", "csv") == "hello_world.csv"
    assert export_filename("", "txt") == "reading_list.txt"


def test_export_filename_truncates_long_query():
    name = export_filename("a" * 200, "bib")
    assert name.endswith(".bib")
    assert len(name) <= 64
