"""Export the reading list to BibTeX, CSV and plain text.

These are pure functions (no Streamlit dependency) so they are unit-testable
and reusable outside the UI. The UI layer turns the returned strings into
``st.download_button`` payloads.
"""

from __future__ import annotations

import csv
import io
import re

from .scholar import Paper, format_citation

_CSV_HEADER = ("title", "authors", "year", "venue", "cited_by", "link")


def reading_list_csv(papers: list[Paper]) -> str:
    """One row per paper, authors joined with ``; ``."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_HEADER)
    for paper in papers:
        writer.writerow([
            paper.title,
            "; ".join(paper.authors),
            paper.year or "",
            paper.venue,
            paper.cited_by,
            paper.link,
        ])
    return buffer.getvalue()


def reading_list_bib(papers: list[Paper]) -> str:
    """All papers as ``@article`` blocks separated by blank lines."""
    return "\n\n".join(format_citation(paper, "bibtex") for paper in papers)


def reading_list_txt(papers: list[Paper], style: str) -> str:
    """One citation per line, formatted in the given style (ABNT, APA, ...)."""
    return "\n\n".join(format_citation(paper, style) for paper in papers)


def export_filename(query: str, extension: str) -> str:
    """A safe, lowercase filename slug for the export.

    Runs of non-alphanumeric characters collapse to a single ``_`` (so
    ``"Hello, World!!"`` becomes ``hello_world``, not ``hello__world``).
    """
    slug = "".join(
        char.lower() if char.isalnum() else "_"
        for char in (query or "reading_list").strip()
    )
    slug = re.sub(r"_+", "_", slug).strip("_")
    slug = slug[:60] or "reading_list"
    return f"{slug}.{extension}"
