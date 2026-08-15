from serpapi_challenge26.scholar import (
    Paper,
    Scholar,
    _scan_years,
    extract_year,
    extract_venue,
    format_abnt,
    format_apa,
    format_citation,
)


def test_scan_years_extracts_full_years():
    assert _scan_years("Foo 2021 - Bar 1999") == [2021, 1999]
    assert _scan_years("no years here") == []


def test_scan_years_ignores_out_of_range_years():
    assert _scan_years("1899 and 2100") == []


def test_extract_year_prefers_latest():
    assert extract_year("X, 2018 ... 2021 - Y") == 2021
    assert extract_year("nothing") is None


def test_extract_venue_strips_truncation_and_trailing_year():
    assert extract_venue("A, B - : Data Mining and …, 2021 - Source") == "Data Mining and"
    assert extract_venue("") == ""


def test_format_abnt_multiple_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima"], venue="Revista X", year=2021)
    assert format_abnt(paper) == "SOUZA, A.; LIMA, B. A title. Revista X, 2021."


def test_format_abnt_no_venue_no_double_dot():
    paper = Paper(title="A title", authors=["Ana Souza"], year=2021)
    assert format_abnt(paper) == "SOUZA, A. A title. 2021."


def test_format_abnt_no_authors():
    paper = Paper(title="A title", year=2021)
    assert format_abnt(paper).startswith("A title")


def test_format_apa_multiple_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima", "Caio Reis"], year=2020)
    assert format_apa(paper) == "Souza, A., Lima, B., & Reis, C. (2020). A title."


def test_format_apa_without_authors_or_year():
    paper = Paper(title="A title")
    assert format_apa(paper) == "(s.a.) (s.d.). A title."


def test_particles_are_not_initials():
    paper = Paper(title="A title", authors=["João Carlos da Silva"], year=2020)
    assert format_apa(paper) == "Silva, J. C. (2020). A title."


def test_format_citation_dispatches_by_style():
    paper = Paper(title="A title", authors=["Ana Souza"], year=2020)
    assert format_citation(paper, "abnt").startswith("SOUZA")
    assert format_citation(paper, "APA").startswith("Souza")


def test_filter_papers_by_year_and_limit():
    papers = [
        Paper(title="a", year=2018),
        Paper(title="b", year=2021),
        Paper(title="c", year=None),
        Paper(title="d", year=2024),
    ]
    filtered = Scholar.filter_papers(papers, year_low=2020, year_high=2025, limit=10)
    assert [paper.title for paper in filtered] == ["b", "c", "d"]


def test_filter_papers_keeps_unknown_years():
    papers = [Paper(title="a", year=2010), Paper(title="b", year=None)]
    filtered = Scholar.filter_papers(papers, year_low=2020, year_high=2025)
    assert [paper.title for paper in filtered] == ["b"]


class _FakeResults(dict):
    def __init__(self, papers, has_next):
        super().__init__(organic_results=papers, pagination={"next": "x"} if has_next else {})


class _FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = 0

    def search(self, params):
        self.calls += 1
        return self.pages.pop(0)


def _raw(title, year):
    return {
        "title": title,
        "publication_info": {"summary": f"A - Venue, {year} - Src"},
        "inline_links": {},
        "snippet": "",
        "resources": [],
    }


def test_search_all_respects_max_results_and_paginates():
    page1 = _FakeResults([_raw(f"p{i}", 2020) for i in range(20)], has_next=True)
    page2 = _FakeResults([_raw(f"q{i}", 2020) for i in range(20)], has_next=False)
    client = _FakeClient([page1, page2])
    scholar = Scholar(client)

    papers = scholar.search_all("x", max_results=25)
    assert len(papers) == 25
    assert client.calls == 2


def test_search_all_stops_when_no_next():
    page1 = _FakeResults([_raw(f"p{i}", 2020) for i in range(20)], has_next=False)
    client = _FakeClient([page1])
    scholar = Scholar(client)

    papers = scholar.search_all("x", max_results=50)
    assert len(papers) == 20
    assert client.calls == 1
