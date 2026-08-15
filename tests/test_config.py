import os

import pytest

from serpapi_challenge26 import config

_ENV_KEYS = ("SERPAPIKEY", "SERPAPI_MODE", "OTHER")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Isolate tests from leaked os.environ state and the real project .env."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


# --- load_env ---------------------------------------------------------------


def test_load_env_sets_new_variables(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SERPAPIKEY=abc123\n"
        "SERPAPI_MODE=record\n",
        encoding="utf-8",
    )

    config.load_env(env_file)
    assert os.environ["SERPAPIKEY"] == "abc123"
    assert os.environ["SERPAPI_MODE"] == "record"


def test_load_env_does_not_override_existing_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SERPAPIKEY", "from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("SERPAPIKEY=from-file\n", encoding="utf-8")

    config.load_env(env_file)
    assert os.environ["SERPAPIKEY"] == "from-shell"


def test_load_env_ignores_comments_and_blank_lines(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\n"
        "\n"
        "   \n"
        "SERPAPIKEY=key\n"
        "   # indented comment\n"
        "SERPAPI_MODE=online\n",
        encoding="utf-8",
    )

    config.load_env(env_file)
    assert os.environ["SERPAPIKEY"] == "key"
    assert os.environ["SERPAPI_MODE"] == "online"


def test_load_env_strips_quotes_and_whitespace(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'SERPAPIKEY="quoted-value"  \n'
        "SERPAPI_MODE='single-quoted'\n"
        "OTHER= spaced value \n",
        encoding="utf-8",
    )

    config.load_env(env_file)
    assert os.environ["SERPAPIKEY"] == "quoted-value"
    assert os.environ["SERPAPI_MODE"] == "single-quoted"
    assert os.environ["OTHER"] == "spaced value"


def test_load_env_skips_lines_without_equals(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("no-equals-here\nSERPAPIKEY=ok\n", encoding="utf-8")

    config.load_env(env_file)
    assert "no-equals-here" not in os.environ
    assert os.environ["SERPAPIKEY"] == "ok"


def test_load_env_missing_file_is_a_noop(tmp_path):
    missing = tmp_path / "does-not-exist.env"
    config.load_env(missing)  # must not raise
    assert "SERPAPIKEY" not in os.environ


def test_load_env_keeps_inline_comment_as_part_of_value(tmp_path):
    # Current behavior: inline "#" is NOT stripped, so the whole tail is the value.
    env_file = tmp_path / ".env"
    env_file.write_text("SERPAPIKEY=key # trailing\n", encoding="utf-8")

    config.load_env(env_file)
    assert os.environ["SERPAPIKEY"] == "key # trailing"


# --- get_api_key ------------------------------------------------------------
# get_api_key() calls load_env() against the CWD ".env"


def test_get_api_key_from_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPIKEY", "env-key")
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    assert config.get_api_key() == "env-key"


def test_get_api_key_from_streamlit_secret(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: "secret-key")
    assert config.get_api_key() == "secret-key"


def test_get_api_key_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    assert config.get_api_key() is None


def test_get_api_key_prefers_environment_over_secret(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPIKEY", "env-key")
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: "secret-key")
    assert config.get_api_key() == "env-key"


# --- _streamlit_secret ------------------------------------------------------


def test_streamlit_secret_returns_none_when_streamlit_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "streamlit":
            raise ImportError("no streamlit")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert config._streamlit_secret("SERPAPIKEY") is None


def test_streamlit_secret_returns_value_when_present(monkeypatch):
    import sys
    import types

    class FakeSecrets:
        def get(self, name):
            return {"SERPAPIKEY": "from-secrets"}.get(name)

    fake_st = types.ModuleType("streamlit")
    fake_st.secrets = FakeSecrets()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    assert config._streamlit_secret("SERPAPIKEY") == "from-secrets"
    assert config._streamlit_secret("MISSING") is None


def test_streamlit_secret_swallows_secrets_exceptions(monkeypatch):
    import sys
    import types

    class BrokenSecrets:
        def get(self, name):
            raise RuntimeError("boom")

    fake_st = types.ModuleType("streamlit")
    fake_st.secrets = BrokenSecrets()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    assert config._streamlit_secret("SERPAPIKEY") is None


# --- get_mode ---------------------------------------------------------------


def test_get_mode_from_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPI_MODE", "record")
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    assert config.get_mode() == "record"


def test_get_mode_is_case_and_whitespace_insensitive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPI_MODE", "  RECORD ")
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    assert config.get_mode() == "record"


def test_get_mode_falls_back_to_default_when_unset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    assert config.get_mode() == "replay"


def test_get_mode_custom_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    assert config.get_mode(default="online") == "online"


def test_get_mode_rejects_invalid_value_and_uses_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPI_MODE", "banana")
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    assert config.get_mode() == "replay"


def test_get_mode_from_streamlit_secret(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: "online")
    assert config.get_mode() == "online"


def test_get_mode_environment_takes_precedence_over_secret(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPI_MODE", "record")
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: "online")
    assert config.get_mode() == "record"
