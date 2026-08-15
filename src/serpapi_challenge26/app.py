"""Gap Finder — Streamlit UI."""

from __future__ import annotations

import streamlit as st

from serpapi_challenge26 import (
    CURRENT_YEAR,
    CachingClient,
    CacheMiss,
    GapAnalyzer,
    Scholar,
    _,
    detect_lang,
    format_citation,
    format_decimal,
    format_int,
    format_percent,
    get_api_key,
    get_mode,
    set_language,
)

_DIRECTION_TEXTS = {
    "underexplored": "Underexplored subtopics (few papers, low citations): %(terms)s.",
    "stagnant": "Citations are still concentrated on older work — a recent result with no strong follow-up is a candidate gap.",
    "cooling": "Low publication activity in the last 3 years: verify whether the field declined or a space opened.",
    "open_questions": "%(count)s paper(s) explicitly declare open questions / future work.",
    "saturated": "Field looks saturated and recent — consider a narrower niche or a cross-domain angle.",
}

_WIDE_OPEN = 70
_SOME_GAPS = 45
_MAX_PAPERS = 50

_CSS = """
<style>
:root {
  --ink: #e7eaf2;
  --muted: #8b93a7;
  --accent: #e0a83d;
  --panel: #141b33;
  --line: #232c47;
}
.stApp { background: #0d1224; color: var(--ink); }
.block-container { max-width: 1080px; padding-top: 2rem; }
h1, h2, h3 {
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  letter-spacing: -0.01em;
}
.eyebrow {
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.4rem;
}
.hero {
  background: #101731;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 1.75rem 2.25rem;
  margin: 1.25rem 0 1.75rem;
}
.hero-label {
  color: var(--muted);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.hero-score {
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-size: 4.25rem;
  font-weight: 600;
  line-height: 1;
  color: var(--ink);
  text-shadow: 0 0 34px rgba(224, 168, 61, 0.28);
}
.hero-score .unit { font-size: 1.25rem; color: var(--muted); font-weight: 400; }
.hero-note { color: var(--accent); font-size: 1.05rem; margin-top: 0.4rem; }
.hero-subs { margin-top: 1rem; }
.badge {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  font-size: 0.75rem;
  color: var(--muted);
  margin-right: 0.4rem;
}
.badge-accent { color: var(--accent); border-color: var(--accent); }
</style>
"""


def _lang() -> str:
    override = st.session_state.get("lang")
    if override:
        return override
    return detect_lang()


def _score_label(score: int) -> str:
    if score >= _WIDE_OPEN:
        return _("Wide open")
    if score >= _SOME_GAPS:
        return _("Some gaps")
    return _("Crowded")


def _badge(text: str, accent: bool = False) -> str:
    css_class = "badge badge-accent" if accent else "badge"
    return f'<span class="{css_class}">{text}</span>'


def _direction_message(direction: dict) -> str:
    message = _DIRECTION_TEXTS[direction["id"]]
    if "terms" in direction:
        message = message % {"terms": direction["terms"]}
    if "count" in direction:
        message = message % {"count": direction["count"]}
    return _(message)


def _render_hero(report) -> None:
    sub = (
        f'<span class="badge">{_("Temporal")} {report.temporal["score"]}</span>'
        f'<span class="badge">{_("Whitespace")} {report.whitespace["score"]}</span>'
        f'<span class="badge">{_("Stagnation")} {report.stagnation["score"]}</span>'
        f'<span class="badge">{_("Open")} {report.open_questions["score"]}</span>'
    )
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-label">{_("Gap opportunity score")}</div>
          <div class="hero-score">{report.score}<span class="unit">/100</span></div>
          <div class="hero-note">{_score_label(report.score)}</div>
          <div class="hero-subs">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_directions(directions: list[dict]) -> None:
    for direction in directions:
        st.markdown(f"- {_direction_message(direction)}")


def _render_temporal(temporal: dict) -> None:
    if temporal["recent_ratio"] is not None:
        st.write(f"{_('Share of papers from the last 3 years')}: **{format_percent(temporal['recent_ratio'])}**")
    if temporal["histogram"]:
        st.bar_chart(temporal["histogram"])


def _render_whitespace(whitespace: dict) -> None:
    if whitespace["underexplored_terms"]:
        st.caption(_("Underexplored terms"))
        for item in whitespace["underexplored_terms"]:
            st.write(
                f"- `{item['term']}` — {item['papers']} {_('papers')}, "
                f"~{format_decimal(item['avg_cites'])} {_('citations')}"
            )
    else:
        st.write(_("No results found."))
    if whitespace["hot_terms"]:
        st.caption(_("Hot terms"))
        st.write(", ".join(f"`{term['term']}`" for term in whitespace["hot_terms"]))


def _render_stagnation(stagnation: dict) -> None:
    if stagnation["avg_top_year"]:
        st.write(
            _("Top-5 year: %(avg_year)s · top-3 share: %(share)s")
            % {"avg_year": format_decimal(stagnation["avg_top_year"]), "share": format_percent(stagnation["top3_share"])}
        )
    if stagnation["top_papers"]:
        st.caption(_("Most-cited papers"))
        for paper in stagnation["top_papers"]:
            st.write(f"- {format_int(paper['cited_by'])} {_('citations')} — {paper['title']}")


def _render_open_questions(open_questions: dict) -> None:
    st.write(f"**{open_questions['count']}**")
    for paper in open_questions["papers"]:
        st.write(f"- {paper['title']}")


def _render_reading_list(papers, style: str) -> None:
    for index, paper in enumerate(papers, 1):
        with st.expander(f"{index}. {paper.title}"):
            st.write(format_citation(paper, style))
            if paper.link:
                st.caption(paper.link)
            if paper.pdf:
                st.caption(f"PDF: {paper.pdf}")


def _render_report(report, papers, style: str) -> None:
    _render_hero(report)

    directions, temporal, whitespace, stagnation, open_questions, reading = st.tabs([
        _("Directions"),
        _("Temporal density"),
        _("Subtopic whitespace"),
        _("Citation stagnation"),
        _("Open questions"),
        _("Reading list"),
    ])

    with directions:
        _render_directions(report.directions)
    with temporal:
        _render_temporal(report.temporal)
    with whitespace:
        _render_whitespace(report.whitespace)
    with stagnation:
        _render_stagnation(report.stagnation)
    with open_questions:
        _render_open_questions(report.open_questions)
    with reading:
        _render_reading_list(papers, style)


def _status_badges(api_key: str | None, mode: str) -> str:
    mode_text = _("Offline mode") if mode == "replay" else _("Online mode")
    badges = _badge(mode_text, accent=mode == "replay")
    if not api_key:
        badges += _badge(_("No API key"))
    return badges


def main() -> None:
    st.set_page_config(page_title="Gap Finder", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    set_language(_lang())

    api_key = get_api_key()
    mode = get_mode()

    with st.sidebar:
        st.radio("Idioma / Language", ["pt", "en"], index=1 if _lang() == "en" else 0, key="lang", horizontal=True)
        st.divider()
        query = st.text_input(_("Research topic"), value="explainable artificial intelligence")
        num = st.slider(_("Number of papers"), 5, 50, 20, step=5)
        yl, yh = st.slider(_("Year window (start–end)"), 2000, CURRENT_YEAR, (2000, CURRENT_YEAR), step=1)
        default_style = "ABNT" if _lang() == "pt" else "APA"
        style = st.selectbox(_("Citation style"), ["APA", "ABNT"], index=0 if default_style == "APA" else 1)
        run = st.button(_("Analyze gaps"), type="primary", use_container_width=True)

    st.markdown('<div class="eyebrow">SerpApi · Google Scholar</div>', unsafe_allow_html=True)
    st.title(_("Gap Finder — find the space in the literature"))
    st.caption(_("Google Scholar search + local research-gap analysis."))
    st.markdown(_status_badges(api_key, mode), unsafe_allow_html=True)

    if not api_key:
        st.info(_("No API key — running offline (fixtures). Set SERPAPIKEY and `record`/`online` mode for live data."))
    if mode == "replay":
        st.info(_("Offline (replay): using fixtures, zero credits."))

    if not run:
        return

    client = CachingClient(api_key=api_key, mode=mode)
    scholar = Scholar(client)

    with st.spinner(_("Searching and analyzing…")):
        try:
            results = scholar.search(query, num=_MAX_PAPERS, hl="en")
            papers = Scholar.parse(results)
        except CacheMiss as exc:
            st.error(str(exc))
            return

    papers = Scholar.filter_papers(papers, year_low=yl, year_high=yh)
    if not papers:
        st.warning(_("No results found."))
        return

    report = GapAnalyzer(papers).analyze()
    display_papers = papers[:num]
    _render_report(report, display_papers, style)


if __name__ == "__main__":
    main()
