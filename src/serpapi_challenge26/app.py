"""Gap Finder — Streamlit UI."""

from __future__ import annotations

import streamlit as st

from .caching import CachingClient, CacheMiss
from .config import get_api_key, get_mode
from .gap import GapAnalyzer
from .scholar import CURRENT_YEAR, Scholar, format_citation


def _lang() -> str:
    return "pt" if st.session_state.get("lang", "pt") == "pt" else "en"


T = {
    "pt": {
        "title": "Gap Finder — encontre o espaço na literatura",
        "subtitle": "Busca no Google Scholar + análise local de lacunas de pesquisa.",
        "query": "Tema de pesquisa",
        "num": "Número de papers",
        "years": "Janela de anos (início–fim)",
        "style": "Formato de citação",
        "run": "Analisar lacunas",
        "loading": "Buscando e analisando…",
        "gap_score": "Índice de oportunidade de gap",
        "directions": "Direções sugeridas",
        "temporal": "Densidade temporal",
        "whitespace": "Whitespace de subtópicos",
        "stagnation": "Estagnação de citações",
        "open": "Questões abertas declaradas",
        "reading": "Reading list",
        "no_results": "Nenhum resultado encontrado.",
        "recent_ratio": "Fração de papers dos últimos 3 anos",
        "papers": "papers",
        "cites": "citações",
        "top_papers": "Papers mais citados",
        "underexplored": "Termos pouco explorados",
        "hot_terms": "Termos quentes",
        "no_key": "Sem chave — rodando offline (fixtures). Defina SERPAPIKEY e o modo `record`/`online` para dados ao vivo.",
        "offline": "Modo offline (replay): usando fixtures, zero crédito.",
        "year": "Ano",
    },
    "en": {
        "title": "Gap Finder — find the space in the literature",
        "subtitle": "Google Scholar search + local research-gap analysis.",
        "query": "Research topic",
        "num": "Number of papers",
        "years": "Year window (start–end)",
        "style": "Citation style",
        "run": "Analyze gaps",
        "loading": "Searching and analyzing…",
        "gap_score": "Gap opportunity score",
        "directions": "Suggested directions",
        "temporal": "Temporal density",
        "whitespace": "Subtopic whitespace",
        "stagnation": "Citation stagnation",
        "open": "Declared open questions",
        "reading": "Reading list",
        "no_results": "No results found.",
        "recent_ratio": "Share of papers from the last 3 years",
        "papers": "papers",
        "cites": "citations",
        "top_papers": "Most-cited papers",
        "underexplored": "Underexplored terms",
        "hot_terms": "Hot terms",
        "no_key": "No API key — running offline (fixtures). Set SERPAPIKEY and `record`/`online` mode for live data.",
        "offline": "Offline (replay): using fixtures, zero credits.",
        "year": "Year",
    },
}


def _t(key: str) -> str:
    return T[_lang()][key]


def _render_report(report, papers, style: str) -> None:
    t = _lang()

    st.metric(_t("gap_score"), f"{report.score}/100")

    st.subheader(_t("directions"))
    for d in report.directions:
        st.write(f"- {d[t]}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(_t("temporal"))
        temp = report.temporal
        if temp["recent_ratio"] is not None:
            st.write(f"{_t('recent_ratio')}: **{temp['recent_ratio']:.0%}**")
        if temp["histogram"]:
            st.bar_chart(temp["histogram"])

        st.subheader(_t("whitespace"))
        if report.whitespace["underexplored_terms"]:
            st.caption(_t("underexplored"))
            for item in report.whitespace["underexplored_terms"]:
                st.write(f"- `{item['term']}` — {item['papers']} {_t('papers')}, ~{item['avg_cites']} {_t('cites')}")
        else:
            st.write(_t("no_results"))
        if report.whitespace["hot_terms"]:
            st.caption(_t("hot_terms"))
            st.write(", ".join(f"`{i['term']}`" for i in report.whitespace["hot_terms"]))

    with col2:
        st.subheader(_t("stagnation"))
        stag = report.stagnation
        if stag["avg_top_year"]:
            st.write(f"Top-5 média {_t('year')}: **{stag['avg_top_year']}** · top-3 share: **{stag['top3_share']:.0%}**")
        if stag["top_papers"]:
            st.caption(_t("top_papers"))
            for p in stag["top_papers"]:
                st.write(f"- {p['cited_by']} {_t('cites')} — {p['title']}")

        st.subheader(_t("open"))
        oq = report.open_questions
        st.write(f"**{oq['count']}**")
        for p in oq["papers"]:
            st.write(f"- {p['title']}")

    st.subheader(_t("reading"))
    for i, paper in enumerate(papers, 1):
        with st.expander(f"{i}. {paper.title}"):
            st.write(format_citation(paper, style))
            if paper.link:
                st.caption(paper.link)
            if paper.pdf:
                st.caption(f"PDF: {paper.pdf}")


def main() -> None:
    st.set_page_config(page_title="Gap Finder", layout="wide")
    st.title(_t("title"))
    st.caption(_t("subtitle"))

    with st.sidebar:
        st.radio("Idioma / Language", ["pt", "en"], key="lang", horizontal=True)

    api_key = get_api_key()
    mode = get_mode()

    if not api_key:
        st.info(_t("no_key"))
    if mode == "replay":
        st.info(_t("offline"))

    query = st.text_input(_t("query"), value="explainable artificial intelligence")
    num = st.slider(_t("num"), 5, 50, 20, step=5)
    yl, yh = st.slider(_t("years"), 2000, CURRENT_YEAR, (2000, CURRENT_YEAR), step=1)
    style = st.selectbox(_t("style"), ["APA", "ABNT"])

    if st.button(_t("run"), type="primary"):
        client = CachingClient(api_key=api_key, mode=mode)
        scholar = Scholar(client)

        with st.spinner(_t("loading")):
            try:
                results = scholar.search(
                    query, num=num, year_low=yl, year_high=yh
                )
                papers = Scholar.parse(results)
            except CacheMiss as exc:
                st.error(str(exc))
                return

        if not papers:
            st.warning(_t("no_results"))
            return

        report = GapAnalyzer(papers).analyze()
        _render_report(report, papers, style)


if __name__ == "__main__":
    main()
