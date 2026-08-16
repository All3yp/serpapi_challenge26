"""Streamlit Cloud entry point.

Community Cloud runs ``streamlit run streamlit_app.py`` from the repo root,
where the ``src/`` layout package is not importable without an editable
install. This shim puts ``src/`` on ``sys.path`` and delegates to the real
app, so deployment needs no build step.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gap_finder.app import main  # noqa: E402

main()
