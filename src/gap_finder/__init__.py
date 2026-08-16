"""Gap Finder — research-gap discovery built on SerpApi (Google Scholar)."""

from __future__ import annotations

from .caching import CacheMiss, CachingClient
from .config import get_api_key, get_mode
from .gap import GapAnalyzer
from .i18n import _, detect_lang, format_decimal, format_int, format_percent, ngettext, set_language
from .scholar import (
    CURRENT_YEAR,
    Paper,
    Scholar,
    format_bibtex,
    format_chicago,
    format_citation,
    format_ieee,
    format_mla,
    format_vancouver,
)

__version__ = "0.1.0"

__all__ = [
    "CachingClient",
    "CacheMiss",
    "get_api_key",
    "get_mode",
    "GapAnalyzer",
    "_",
    "ngettext",
    "detect_lang",
    "format_decimal",
    "format_int",
    "format_percent",
    "set_language",
    "CURRENT_YEAR",
    "Paper",
    "Scholar",
    "format_citation",
    "format_ieee",
    "format_bibtex",
    "format_vancouver",
    "format_mla",
    "format_chicago",
]


def main() -> None:
    """Launch the Streamlit app."""
    import os

    from streamlit.web import cli as stcli

    this_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(this_dir, "app.py")
    stcli.main(["run", app_path])
