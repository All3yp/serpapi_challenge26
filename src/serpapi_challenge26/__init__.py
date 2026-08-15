"""SerpApi Nordeste Coding Challenge 2026 — Gap Finder."""

from __future__ import annotations

__all__ = ["app", "caching", "config", "gap", "scholar"]

__version__ = "0.1.0"


def main() -> None:
    """Launch the Streamlit app."""
    import os

    from streamlit.web import cli as stcli

    this_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(this_dir, "app.py")
    stcli.main(["run", app_path])
