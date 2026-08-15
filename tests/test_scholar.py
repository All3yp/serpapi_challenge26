from serpapi_challenge26.scholar import (
    Paper,
    Scholar,
    _coerce_int,
    _scan_years,
    extract_year,
    extract_venue,
    format_abnt,
    format_apa,
    format_bibtex,
    format_chicago,
    format_citation,
    format_ieee,
    format_mla,
    format_vancouver,
)


def test_scan_years_extracts_full_years():
    assert _scan_years("Foo 2021 - Bar 1999") == [2021, 1999]
    assert _scan_years("no years here") == []


def test_scan_years_ignores_out_of_range_years():
    assert _scan_years("1899 and 2100") == []


def test_extract_year_prefers_latest():
    assert extract_year("X, 2018 ... 2021 - Y") == 2021
    assert extract_year("nothing") is None


def test_extract_year_handles_falsy_input():
    assert extract_year(None) is None
    assert extract_year("") is None


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


def test_mononym_author_no_stray_comma_or_space():
    paper = Paper(title="A title", authors=["Silva"], year=2020)
    assert format_apa(paper) == "Silva (2020). A title."
    assert format_abnt(paper) == "SILVA A title. 2020."
    assert format_chicago(paper) == 'Silva. 2020. "A title."'


def test_particles_are_not_initials():
    paper = Paper(title="A title", authors=["João Carlos da Silva"], year=2020)
    assert format_apa(paper) == "Silva, J. C. (2020). A title."


def test_format_citation_dispatches_by_style():
    paper = Paper(title="A title", authors=["Ana Souza"], year=2020)
    assert format_citation(paper, "abnt").startswith("SOUZA")
    assert format_citation(paper, "APA").startswith("Souza")


def test_format_ieee_single_author():
    paper = Paper(title="A title", authors=["João Carlos da Silva"], venue="Revista X", year=2021)
    assert format_ieee(paper) == 'J. C. Silva, "A title," Revista X, 2021.'


def test_format_ieee_two_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima"], venue="Revista X", year=2020)
    assert format_ieee(paper) == 'A. Souza and B. Lima, "A title," Revista X, 2020.'


def test_format_ieee_three_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima", "Caio Reis"], year=2020)
    assert format_ieee(paper) == 'A. Souza, B. Lima, and C. Reis, "A title," 2020.'


def test_format_ieee_no_authors_no_venue():
    paper = Paper(title="A title", year=2020)
    assert format_ieee(paper) == '"A title," 2020.'


def test_format_bibtex_full():
    paper = Paper(
        title="A title",
        authors=["Ana Souza", "Bia Lima"],
        venue="Revista X",
        year=2020,
        link="http://example.com",
    )
    bib = format_bibtex(paper)
    assert bib.startswith("@article{souza2020a,")
    assert "author = {Souza, Ana and Lima, Bia}," in bib
    assert "title = {A title}," in bib
    assert "year = {2020}," in bib
    assert "journal = {Revista X}," in bib
    assert "url = {http://example.com}," in bib


def test_format_bibtex_minimal():
    paper = Paper(title="A title")
    bib = format_bibtex(paper)
    assert bib.startswith("@article{a,")
    assert "title = {A title}," in bib


def test_format_bibtex_escapes_special_characters():
    paper = Paper(title="Machine Learning & Graph RAG", authors=["Ana Souza"], year=2024)
    bib = format_bibtex(paper)
    assert "title = {Machine Learning \\& Graph RAG}," in bib


def test_format_bibtex_distinct_keys_for_same_author_year():
    first = format_bibtex(Paper(title="Machine learning survey", authors=["Ana Souza"], year=2020))
    second = format_bibtex(Paper(title="Graph neural networks", authors=["Ana Souza"], year=2020))
    assert first.splitlines()[0] != second.splitlines()[0]


def test_format_citation_dispatches_ieee_and_bibtex():
    paper = Paper(title="A title", authors=["Ana Souza"], year=2020)
    assert format_citation(paper, "IEEE").startswith("A. Souza")
    assert format_citation(paper, "bibtex").startswith("@article{")
    assert format_citation(paper, "BIB").startswith("@article{")


def test_format_vancouver_single_author():
    paper = Paper(title="A title", authors=["João Carlos da Silva"], venue="Revista X", year=2021)
    assert format_vancouver(paper) == "Silva JC. A title. Revista X. 2021"


def test_format_vancouver_multiple_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima"], year=2020)
    assert format_vancouver(paper) == "Souza A, Lima B. A title. 2020"


def test_format_vancouver_more_than_six_authors():
    authors = [f"Author{i} Last{i}" for i in range(8)]
    paper = Paper(title="A title", authors=authors, year=2020)
    result = format_vancouver(paper)
    assert result.endswith("et al. A title. 2020")
    assert result.count(",") == 6  # 6 authors joined by 5 commas + 1 before "et al"


def test_format_mla_two_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima"], venue="Revista X", year=2020)
    assert format_mla(paper) == 'Souza, Ana, and Bia Lima. "A title." Revista X, 2020.'


def test_format_mla_three_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima", "Caio Reis"], year=2020)
    assert format_mla(paper) == 'Souza, Ana, et al. "A title." 2020.'


def test_format_mla_no_authors():
    paper = Paper(title="A title", year=2020)
    assert format_mla(paper) == '"A title." 2020.'


def test_format_vancouver_no_authors():
    paper = Paper(title="A title", year=2020)
    assert format_vancouver(paper) == "A title. 2020"


def test_format_chicago_single_author():
    paper = Paper(title="A title", authors=["Ana Souza"], venue="Revista X", year=2020)
    assert format_chicago(paper) == 'Souza, Ana. 2020. "A title." Revista X.'


def test_format_chicago_multiple_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima"], year=2020)
    assert format_chicago(paper) == 'Souza, Ana, Lima, Bia. 2020. "A title."'


def test_format_chicago_no_authors():
    paper = Paper(title="A title", year=2020)
    assert format_chicago(paper) == '2020. "A title."'


def test_format_citation_dispatches_new_styles():
    paper = Paper(title="A title", authors=["Ana Souza"], year=2020)
    assert format_citation(paper, "vancouver").endswith("2020")
    assert format_citation(paper, "mla").startswith("Souza")
    assert format_citation(paper, "chicago").startswith("Souza")


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


class _RecordingClient:
    def __init__(self, pages):
        self.pages = pages
        self.seen_params = []

    def search(self, params):
        self.seen_params.append(params)
        return self.pages.pop(0)


def test_search_all_forwards_year_filter_to_search():
    page1 = _FakeResults([_raw(f"p{i}", 2020) for i in range(20)], has_next=False)
    client = _RecordingClient([page1])
    scholar = Scholar(client)

    scholar.search_all("x", max_results=10, year_low=2015, year_high=2024)
    assert client.seen_params[0]["as_ylo"] == 2015
    assert client.seen_params[0]["as_yhi"] == 2024


def test_search_all_does_not_forward_absent_year_filter():
    page1 = _FakeResults([_raw(f"p{i}", 2020) for i in range(20)], has_next=False)
    client = _RecordingClient([page1])
    scholar = Scholar(client)

    scholar.search_all("x", max_results=10)
    assert "as_ylo" not in client.seen_params[0]
    assert "as_yhi" not in client.seen_params[0]


def test_search_all_stops_at_page_cap():
    # Every page reports has_next=True, so only the page cap terminates the loop.
    pages = [_FakeResults([_raw(f"p{i}", 2020) for i in range(20)], has_next=True)] * 60
    client = _FakeClient(pages)
    scholar = Scholar(client)

    papers = scholar.search_all("x", max_results=5000)
    assert len(papers) == 1000  # 50 pages * 20 papers
    assert client.calls == 50


def test_coerce_int_handles_varied_cited_by_formats():
    assert _coerce_int(444) == 444
    assert _coerce_int("1,234") == 1234
    assert _coerce_int(" 42 ") == 42
    assert _coerce_int(3.0) == 3
    assert _coerce_int(None) == 0
    assert _coerce_int("n/a") == 0
    assert _coerce_int(True) == 1


def test_parse_item_tolerates_non_integer_cited_by():
    raw = {
        "title": "T",
        "publication_info": {"summary": "A - V, 2020 - S"},
        "inline_links": {"cited_by": {"total": "1,234"}},
        "resources": [],
    }
    results = {"organic_results": [raw]}
    paper = Scholar.parse(results)[0]
    assert paper.cited_by == 1234


def test_search_all_stops_when_page_empty():
    # Empty organic_results must terminate even if has_next is truthy.
    empty = _FakeResults([], has_next=True)
    client = _FakeClient([empty])
    scholar = Scholar(client)
    papers = scholar.search_all("x", max_results=50)
    assert papers == []
    assert client.calls == 1


def test_first_pdf_prefers_pdf_format():
    resources = [
        {"file_format": "HTML", "link": "http://h"},
        {"file_format": "PDF", "link": "http://p"},
    ]
    raw = {
        "title": "T",
        "publication_info": {"summary": "A - V, 2020 - S"},
        "inline_links": {},
        "resources": resources,
    }
    paper = Scholar.parse({"organic_results": [raw]})[0]
    assert paper.pdf == "http://p"


def test_drop_trailing_year_strips_comma_year():
    from serpapi_challenge26.scholar import _drop_trailing_year

    assert _drop_trailing_year("Some Venue, 2020") == "Some Venue"
    assert _drop_trailing_year("No year here") == "No year here"


def test_author_initials_skips_empty_and_particles():
    from serpapi_challenge26.scholar import _author_initials

    assert _author_initials("João Carlos da Silva") == "J. C."
    assert _author_initials("Silva") == ""
