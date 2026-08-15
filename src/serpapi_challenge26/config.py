"""Environment and API-key loading with no third-party dependency."""

from __future__ import annotations

import os
from pathlib import Path

_API_KEY_ENV = "SERPAPIKEY"
_MODE_ENV = "SERPAPI_MODE"
VALID_MODES = ("record", "replay", "online")


def load_env(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key() -> str | None:
    load_env()
    return os.environ.get(_API_KEY_ENV) or _streamlit_secret(_API_KEY_ENV)


def _streamlit_secret(name: str) -> str | None:
    try:
        import streamlit as st
    except ImportError:
        return None
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def get_mode(default: str = "replay") -> str:
    load_env()
    mode = os.environ.get(_MODE_ENV) or _streamlit_secret(_MODE_ENV) or default
    mode = mode.strip().lower()
    return mode if mode in VALID_MODES else default
