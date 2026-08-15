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


def _lang() -> str:
    override = st.session_state.get("lang")
    if override:
        return override
    return detect_lang()


def _render_report(report, papers, style: str) -> None:
    st.metric(_("Gap opportunity score"), f"{report.score}/100")

    st.subheader(_("Suggested directions"))
    for direction in report.directions:
        message = _DIRECTION_TEXTS[direction["id"]]
        if "terms" in direction:
            message = message % {"terms": direction["terms"]}
        if "count" in direction:
            message = message % {"count": direction["count"]}
        st.write(f"- {_(message)}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(_("Temporal density"))
        temp = report.temporal
        if temp["recent_ratio"] is not None:
            st.write(f"{_('Share of papers from the last 3 years')}: **{format_percent(temp['recent_ratio'])}**")
        if temp["histogram"]:
            st.bar_chart(temp["histogram"])

        st.subheader(_("Subtopic whitespace"))
        if report.whitespace["underexplored_terms"]:
            st.caption(_("Underexplored terms"))
            for item in report.whitespace["underexplored_terms"]:
                st.write(
                    f"- `{item['term']}` — {item['papers']} {_('papers')}, "
                    f"~{format_decimal(item['avg_cites'])} {_('citations')}"
                )
        else:
            st.write(_("No results found."))
        if report.whitespace["hot_terms"]:
            st.caption(_("Hot terms"))
            st.write(", ".join(f"`{i['term']}`" for i in report.whitespace["hot_terms"]))

    with col2:
        st.subheader(_("Citation stagnation"))
        stag = report.stagnation
        if stag["avg_top_year"]:
            st.write(
                _("Top-5 year: %(avg_year)s · top-3 share: %(share)s")
                % {"avg_year": format_decimal(stag["avg_top_year"]), "share": format_percent(stag["top3_share"])}
            )
        if stag["top_papers"]:
            st.caption(_("Most-cited papers"))
            for paper in stag["top_papers"]:
                st.write(f"- {format_int(paper['cited_by'])} {_('citations')} — {paper['title']}")

        st.subheader(_("Declared open questions"))
        open_questions = report.open_questions
        st.write(f"**{open_questions['count']}**")
        for paper in open_questions["papers"]:
            st.write(f"- {paper['title']}")

    st.subheader(_("Reading list"))
    for i, paper in enumerate(papers, 1):
        with st.expander(f"{i}. {paper.title}"):
            st.write(format_citation(paper, style))
            if paper.link:
                st.caption(paper.link)
            if paper.pdf:
                st.caption(f"PDF: {paper.pdf}")


def main() -> None:
    st.set_page_config(page_title="Gap Finder", layout="wide")
    set_language(_lang())
    st.title(_("Gap Finder — find the space in the literature"))
    st.caption(_("Google Scholar search + local research-gap analysis."))

    with st.sidebar:
        st.radio("Idioma / Language", ["pt", "en"], key="lang", horizontal=True)

    api_key = get_api_key()
    mode = get_mode()

    if not api_key:
        st.info(_("No API key — running offline (fixtures). Set SERPAPIKEY and `record`/`online` mode for live data."))
    if mode == "replay":
        st.info(_("Offline (replay): using fixtures, zero credits."))

    query = st.text_input(_("Research topic"), value="explainable artificial intelligence")
    num = st.slider(_("Number of papers"), 5, 50, 20, step=5)
    yl, yh = st.slider(_("Year window (start–end)"), 2000, CURRENT_YEAR, (2000, CURRENT_YEAR), step=1)
    default_style = "ABNT" if _lang() == "pt" else "APA"
    style = st.selectbox(_("Citation style"), ["APA", "ABNT"], index=0 if default_style == "APA" else 1)

    if st.button(_("Analyze gaps"), type="primary"):
        client = CachingClient(api_key=api_key, mode=mode)
        scholar = Scholar(client)

        with st.spinner(_("Searching and analyzing…")):
            try:
                results = scholar.search(query, num=num, year_low=yl, year_high=yh)
                papers = Scholar.parse(results)
            except CacheMiss as exc:
                st.error(str(exc))
                return

        if not papers:
            st.warning(_("No results found."))
            return

        report = GapAnalyzer(papers).analyze()
        _render_report(report, papers, style)


if __name__ == "__main__":
    main()
