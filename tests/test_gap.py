from serpapi_challenge26.gap import GapAnalyzer, THRESHOLDS
from serpapi_challenge26.scholar import Paper


def _paper(title, year, cited_by=0, snippet=""):
    return Paper(title=title, year=year, cited_by=cited_by, snippet=snippet)


def test_analyze_score_is_in_range():
    papers = [_paper(f"Topic {i}", 2020, i) for i in range(10)]
    report = GapAnalyzer(papers).analyze()
    assert 0 <= report.score <= 100


def test_signal_can_reach_full_score_of_100():
    # 12 distinct underexplored terms (all >= 3 chars) -> 40 + 12*5 = 100, at cap.
    title = " ".join([
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta",
        "theta", "iota", "kappa", "lambda", "sigma", "omega",
    ])
    paper = _paper(title, 2020, cited_by=0)
    report = GapAnalyzer([paper]).analyze()
    assert report.whitespace["score"] == 100


def test_score_uses_weighted_average():
    papers = [_paper(f"Topic {i}", 2020, i) for i in range(10)]
    report = GapAnalyzer(papers).analyze()
    scores = [
        report.temporal["score"],
        report.whitespace["score"],
        report.stagnation["score"],
        report.open_questions["score"],
    ]
    expected = round(
        scores[0] * THRESHOLDS.weight_temporal
        + scores[1] * THRESHOLDS.weight_whitespace
        + scores[2] * THRESHOLDS.weight_stagnation
        + scores[3] * THRESHOLDS.weight_open
    )
    assert report.score == expected


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


def test_directions_use_structured_ids():
    papers = [_paper("A study", 2015, snippet="future work is still needed")]
    report = GapAnalyzer(papers).analyze()
    ids = [direction["id"] for direction in report.directions]
    assert "open_questions" in ids
    for direction in report.directions:
        assert "id" in direction


def test_temporal_density_no_years():
    report = GapAnalyzer([_paper("x", None)]).analyze()
    assert report.temporal["note"] == "no_years"
    assert report.temporal["recent_ratio"] is None


def test_temporal_density_hot():
    papers = [_paper(f"T{i}", 2025) for i in range(10)]
    report = GapAnalyzer(papers).analyze()
    assert report.temporal["note"] == "hot"


def test_temporal_density_steady():
    papers = [_paper(f"old{i}", 2015) for i in range(5)]
    papers += [_paper(f"new{i}", 2025) for i in range(5)]
    report = GapAnalyzer(papers).analyze()
    assert report.temporal["note"] == "steady"


def test_citation_stagnation_healthy():
    report = GapAnalyzer([_paper("T", 2025, cited_by=10)]).analyze()
    assert report.stagnation["note"] == "healthy"


def test_directions_saturated_when_no_signal():
    papers = [_paper("common term", 2025) for _ in range(10)]
    report = GapAnalyzer(papers).analyze()
    assert report.directions == [{"id": "saturated"}]
