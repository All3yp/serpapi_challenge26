from serpapi_challenge26.scholar import (
    Paper,
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
    assert format_abnt(paper) == "SOUZA, A.; LIMA, B.. A title. Revista X, 2021."


def test_format_apa_multiple_authors():
    paper = Paper(title="A title", authors=["Ana Souza", "Bia Lima", "Caio Reis"], year=2020)
    assert format_apa(paper) == "Souza, A., Lima, B., & Reis, C. (2020). A title.."


def test_format_apa_without_authors_or_year():
    paper = Paper(title="A title")
    assert format_apa(paper) == "(s.a.) (s.d.). A title.."


def test_format_citation_dispatches_by_style():
    paper = Paper(title="A title", authors=["Ana Souza"], year=2020)
    assert format_citation(paper, "abnt").startswith("SOUZA")
    assert format_citation(paper, "APA").startswith("Souza")
