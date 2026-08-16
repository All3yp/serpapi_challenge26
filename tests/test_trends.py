"""Tests for the Google Trends demand signal (trends.py)."""

from gap_finder.trends import Trends, build_demand


def _results(points):
    """Build a fake google_trends response from a list of (value, ...) values."""
    timeline = []
    for i, value in enumerate(points):
        timeline.append({
            "timestamp": str(1_700_000_000 + i),
            "values": [{"query": "x", "value": str(value), "extracted_value": value}],
        })
    return {"interest_over_time": {"timeline_data": timeline}}


def test_parse_interest_sorts_by_timestamp():
    results = _results([10, 20, 30, 40])
    points = Trends.parse_interest(results)
    assert len(points) == 4
    assert points[0][1] == 10.0
    assert points[-1][1] == 40.0
    # timestamps are monotonic
    stamps = [t for t, _ in points]
    assert stamps == sorted(stamps)


def test_growth_is_second_half_minus_first_half():
    results = _results([10, 10, 30, 30])
    points = Trends.parse_interest(results)
    assert Trends.growth(points) == 20.0


def test_growth_none_when_too_few_points():
    assert Trends.growth([]) is None
    assert Trends.growth([(1, 1.0), (2, 1.0)]) is None


def test_demand_score_maps_flat_to_50():
    assert Trends.demand_score(0.0) == 50.0
    assert Trends.demand_score(10.0) == 70.0  # 50 + 10*2


def test_note_thresholds():
    assert Trends.note(6.0) == "rising"
    assert Trends.note(-6.0) == "falling"
    assert Trends.note(0.0) == "flat"


class _FakeTrendsClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    def search(self, params):
        self.calls += 1
        return self.responses.pop(0)


def test_build_demand_picks_highest_growth_term():
    whitespace = {"underexplored_terms": [
        {"term": "a"},
        {"term": "b"},
        {"term": "c"},
    ]}
    client = _FakeTrendsClient([
        _results([10, 10, 10, 10]),   # a: growth 0
        _results([10, 10, 50, 50]),   # b: growth 40
        _results([10, 10, 20, 20]),   # c: growth 10
    ])
    demand = build_demand(client, whitespace)
    assert demand["term"] == "b"
    assert demand["growth"] == 40.0
    assert demand["note"] == "rising"


def test_build_demand_returns_none_without_terms():
    assert build_demand(_FakeTrendsClient([]), {"underexplored_terms": []}) is None


def test_build_demand_returns_none_when_all_fail():
    class _BoomClient:
        def search(self, params):
            raise RuntimeError("offline")

    whitespace = {"underexplored_terms": [{"term": "a"}]}
    assert build_demand(_BoomClient(), whitespace) is None
