from serpapi_challenge26.gap import GapAnalyzer
from serpapi_challenge26.scholar import Paper


def _paper(title, year, cited_by=0, snippet=""):
    return Paper(title=title, year=year, cited_by=cited_by, snippet=snippet)


def test_analyze_score_is_in_range():
    papers = [_paper(f"Topic {i}", 2020, i) for i in range(10)]
    report = GapAnalyzer(papers).analyze()
    assert 0 <= report.score <= 100


def test_temporal_density_detects_cooling():
    papers = [_paper("old", 2010)] * 5 + [_paper("recent", 2025)]
    report = GapAnalyzer(papers).analyze()
    assert report.temporal["note"] == "cooling"


def test_open_questions_detects_marker():
    papers = [_paper("A study", 2020, snippet="future work is still needed")]
    report = GapAnalyzer(papers).analyze()
    assert report.open_questions["count"] == 1


def test_citation_stagnation_without_citations():
    papers = [_paper("x", 2020)]
    report = GapAnalyzer(papers).analyze()
    assert report.stagnation["note"] == "no_citations"


def test_subtopic_whitespace_returns_terms():
    papers = [
        _paper("Deep learning for vision", 2020, 10),
        _paper("Deep learning for speech", 2021, 8),
        _paper("Quantum computing advances", 2022, 3),
    ]
    report = GapAnalyzer(papers).analyze()
    assert report.whitespace["underexplored_terms"]
