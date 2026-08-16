"""Tests for the Streamlit UI layer (app.py) and the app entry points."""

import importlib
import runpy
import sys
import types

import pytest

from gap_finder.scholar import Paper


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeStreamlit:
    """Minimal stand-in for the ``streamlit`` module surface used by app.py."""

    def __init__(self):
        self.session_state = {}
        self.button_result = False
        self.sidebar = _Ctx()
        self.error_calls = []
        self.warning_calls = []
        self.info_calls = []

    # -- widget/rendering surface -------------------------------------------
    def set_page_config(self, **kwargs):
        pass

    def markdown(self, body, unsafe_allow_html=False):
        pass

    def radio(self, label, options=(), **kwargs):
        return options[0]

    def divider(self):
        pass

    def text_input(self, label, value="", **kwargs):
        return value

    def slider(self, label, *args, **kwargs):
        return args[2] if len(args) > 2 else kwargs.get("value")

    def selectbox(self, label, options, index=0, **kwargs):
        return options[index]

    def button(self, label, **kwargs):
        return self.button_result

    def title(self, body):
        pass

    def caption(self, body):
        pass

    def write(self, body):
        pass

    def bar_chart(self, data):
        pass

    def spinner(self, text=""):
        return _Ctx()

    def tabs(self, tabs):
        return [_Ctx() for _ in tabs]

    def expander(self, label, expanded=False):
        return _Ctx()

    # -- messages (recorded for assertions) ----------------------------------
    def info(self, body):
        self.info_calls.append(body)

    def error(self, body):
        self.error_calls.append(body)

    def warning(self, body):
        self.warning_calls.append(body)


@pytest.fixture
def app(monkeypatch):
    """Return (app module bound to a fake streamlit, fake streamlit instance)."""
    fake = _FakeStreamlit()
    mod = types.ModuleType("streamlit")
    for name in dir(fake):
        if name.startswith("_"):
            continue
        setattr(mod, name, getattr(fake, name))
    monkeypatch.setitem(sys.modules, "streamlit", mod)
    sys.modules.pop("gap_finder.app", None)
    module = importlib.import_module("gap_finder.app")
    return module, fake


class _FakeReport:
    score = 55
    temporal = {"score": 55, "recent_ratio": 0.5, "histogram": {"2020": 1}, "note": "steady"}
    whitespace = {
        "score": 60,
        "underexplored_terms": [{"term": "niche", "papers": 1, "avg_cites": 1.0}],
        "hot_terms": [{"term": "hot"}],
    }
    stagnation = {
        "score": 65,
        "avg_top_year": 2020.0,
        "top3_share": 0.5,
        "note": "healthy",
        "top_papers": [{"title": "T", "cited_by": 10, "year": 2020}],
    }
    open_questions = {"score": 30, "count": 1, "papers": [{"title": "T"}]}
    directions = [{"id": "open_questions", "count": 1}]


# --- pure helpers -----------------------------------------------------------


def test_papers_slider_bounds(app):
    module, _ = app
    assert module._MAX_PAPERS == 100
    assert module._MIN_PAPERS == 5
    assert module._DEFAULT_PAPERS == 20


def test_score_label_thresholds(app):
    module, _ = app
    assert module._score_label(70) == "Wide open"
    assert module._score_label(45) == "Some gaps"
    assert module._score_label(44) == "Crowded"


def test_badge_markup(app):
    module, _ = app
    assert module._badge("x") == '<span class="badge">x</span>'
    assert module._badge("x", accent=True) == '<span class="badge badge-accent">x</span>'


def test_direction_message_substitution(app):
    module, _ = app
    assert module._direction_message({"id": "underexplored", "terms": "foo"}).endswith("foo.")
    assert "3 papers" in module._direction_message({"id": "open_questions", "count": 3})
    assert "saturated" in module._direction_message({"id": "saturated"})


def test_status_badges(app):
    module, _ = app
    assert "badge-accent" in module._status_badges("key", "replay")
    assert "No API key" in module._status_badges(None, "online")
    assert "No API key" not in module._status_badges("key", "online")


def test_status_badges_record_mode(app):
    module, _ = app
    badges = module._status_badges("key", "record")
    assert "Record mode" in badges
    assert "badge-accent" not in badges


def test_status_badges_online_mode(app):
    module, _ = app
    assert "Online mode" in module._status_badges("key", "online")


def test_lang_uses_session_override(app):
    module, fake = app
    fake.session_state["lang"] = "pt"
    assert module._lang() == "pt"


def test_lang_falls_back_to_detection(app, monkeypatch):
    module, _ = app
    monkeypatch.setattr(module, "detect_lang", lambda: "pt")
    assert module._lang() == "pt"


# --- render functions -------------------------------------------------------


def test_render_report_runs_all_tabs(app):
    module, _ = app
    papers = [Paper(title="T", year=2020, link="http://l", pdf="http://p")]
    module._render_report(_FakeReport(), papers, "APA")


def test_render_whitespace_no_results(app):
    module, _ = app
    module._render_whitespace({"underexplored_terms": [], "hot_terms": []})


def test_render_temporal_no_data(app):
    module, _ = app
    module._render_temporal({"recent_ratio": None, "histogram": {}})


def test_render_stagnation_empty(app):
    module, _ = app
    module._render_stagnation({"avg_top_year": None, "top3_share": 0.0, "top_papers": []})


def test_render_reading_list_without_links(app):
    module, _ = app
    module._render_reading_list([Paper(title="T", year=2020)], "ABNT")


# --- main() -----------------------------------------------------------------


def _patch_main(module, monkeypatch, *, api_key="key", mode="online", papers=None, filtered=None, cache_miss=False):
    monkeypatch.setattr(module, "get_api_key", lambda: api_key)
    monkeypatch.setattr(module, "get_mode", lambda: mode)
    monkeypatch.setattr(module, "CachingClient", lambda **kwargs: object())

    if cache_miss:

        class _Scholar:
            def __init__(self, client):
                pass

            def search_all(self, *args, **kwargs):
                raise module.CacheMiss("no fixture")

        monkeypatch.setattr(module, "Scholar", _Scholar)
    else:

        class _Scholar:
            def __init__(self, client):
                pass

            def search_all(self, *args, **kwargs):
                return papers

            @staticmethod
            def filter_papers(ps, **kwargs):
                return filtered if filtered is not None else ps

        monkeypatch.setattr(module, "Scholar", _Scholar)

    class _FakeAnalyzer:
        def __init__(self, papers):
            pass

        def analyze(self):
            return _FakeReport()

    monkeypatch.setattr(module, "GapAnalyzer", _FakeAnalyzer)


def test_main_returns_early_when_not_run(app, monkeypatch):
    module, fake = app
    fake.button_result = False
    _patch_main(module, monkeypatch)
    module.main()


def test_main_full_happy_path(app, monkeypatch):
    module, fake = app
    fake.button_result = True
    papers = [Paper(title="T", year=2020, link="http://l", pdf="http://p")]
    _patch_main(module, monkeypatch, papers=papers)
    module.main()


def test_main_no_results_path(app, monkeypatch):
    module, fake = app
    fake.button_result = True
    papers = [Paper(title="T", year=2020)]
    _patch_main(module, monkeypatch, papers=papers, filtered=[])
    module.main()
    assert len(fake.warning_calls) == 1


def test_main_cache_miss_path(app, monkeypatch):
    module, fake = app
    fake.button_result = True
    _patch_main(module, monkeypatch, cache_miss=True)
    module.main()
    assert len(fake.error_calls) == 1


def test_main_no_api_key_replay_banners(app, monkeypatch):
    module, fake = app
    fake.button_result = False
    _patch_main(module, monkeypatch, api_key=None, mode="replay")
    module.main()
    assert len(fake.info_calls) == 2


def test_main_no_api_key_online_falls_back_to_replay(app, monkeypatch):
    module, fake = app
    fake.button_result = False
    _patch_main(module, monkeypatch, api_key=None, mode="online")
    module.main()
    assert len(fake.warning_calls) == 1
    assert len(fake.info_calls) == 2


# --- entry points -----------------------------------------------------------


def test_package_main_launches_streamlit(monkeypatch):
    calls = []

    streamlit_mod = types.ModuleType("streamlit")
    web_mod = types.ModuleType("streamlit.web")
    cli_mod = types.ModuleType("streamlit.web.cli")

    def fake_main(argv):
        calls.append(argv)

    cli_mod.main = fake_main
    web_mod.cli = cli_mod

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_mod)
    monkeypatch.setitem(sys.modules, "streamlit.web", web_mod)
    monkeypatch.setitem(sys.modules, "streamlit.web.cli", cli_mod)

    import gap_finder as pkg

    pkg.main()
    assert len(calls) == 1
    assert calls[0][0] == "run"
    assert calls[0][1].endswith("app.py")


def test_main_py_entrypoint_calls_main(monkeypatch):
    import gap_finder as pkg

    called = []
    monkeypatch.setattr(pkg, "main", lambda: called.append("ran"))

    runpy.run_path("main.py", run_name="__main__")
    assert called == ["ran"]


def test_app_main_guard_invokes_main(app, monkeypatch):
    module, fake = app
    fake.button_result = False
    _patch_main(module, monkeypatch)
    # Execute app.py as __main__ so its module-level guard runs.
    import os

    app_path = os.path.join(os.path.dirname(module.__file__), "app.py")
    runpy.run_path(app_path, run_name="__main__")
