"""Google Trends demand signal via SerpApi.

The core gap signals are computed 100% offline from Scholar results. This
module adds a *demand* signal: it asks Google Trends whether the niches the
analyzer flagged as "underexplored" actually have rising public interest.

A subtopic that is under-published **and** rising in search is a stronger gap
than one that is merely under-published — this turns the tool from a pure
literature analyst into a literature + market-demand analyst.

Every call goes through the same ``CachingClient`` as Scholar, so it is cached
in ``record`` mode and costs nothing in ``replay`` mode.
"""

from __future__ import annotations

_DATE_WINDOW = "today 5-y"
# Cap the number of Trends lookups per search: each is one credit in
# ``online``/``record`` mode. Checking the top underexplored niches is enough
# to confirm whether a gap has demand.
_MAX_TERMS = 3
# Growth (in raw Trends 0-100 units) beyond which we call a trend "rising".
_RISING_THRESHOLD = 5.0
# Scales raw growth into the 0-100 demand score (flat -> 50).
_GROWTH_SCALE = 2.0


class Trends:
    """Search the ``google_trends`` engine and extract the interest series."""

    def __init__(self, client) -> None:
        self.client = client

    def search(self, q: str, *, date: str = _DATE_WINDOW, hl: str = "en"):
        params = {
            "engine": "google_trends",
            "q": q,
            "data_type": "TIMESERIES",
            "date": date,
            "hl": hl,
        }
        return self.client.search(params)

    @staticmethod
    def parse_interest(results) -> list[tuple[int, float]]:
        """Return ``[(timestamp, extracted_value), ...]`` sorted by timestamp."""
        timeline = (results.get("interest_over_time") or {}).get("timeline_data", [])
        points: list[tuple[int, float]] = []
        for entry in timeline:
            try:
                timestamp = int(entry.get("timestamp") or 0)
            except (TypeError, ValueError):
                timestamp = 0
            for value in entry.get("values", []):
                extracted = value.get("extracted_value")
                if extracted is None:
                    continue
                try:
                    points.append((timestamp, float(extracted)))
                except (TypeError, ValueError):
                    continue
        points.sort(key=lambda point: point[0])
        return points

    @staticmethod
    def growth(points: list[tuple[int, float]]) -> float | None:
        """Raw trend: mean(second half) - mean(first half), in 0-100 units.

        Returns ``None`` when there are too few points to compare halves.
        """
        if len(points) < 4:
            return None
        half = len(points) // 2
        first = [value for _, value in points[:half]]
        second = [value for _, value in points[half:]]
        if not first or not second:
            return None
        return sum(second) / len(second) - sum(first) / len(first)

    @staticmethod
    def demand_score(growth: float) -> float:
        """Map raw growth to a 0-100 opportunity score (flat -> 50)."""
        return max(0.0, min(100.0, 50.0 + growth * _GROWTH_SCALE))

    @staticmethod
    def note(growth: float) -> str:
        if growth >= _RISING_THRESHOLD:
            return "rising"
        if growth <= -_RISING_THRESHOLD:
            return "falling"
        return "flat"


def build_demand(client, whitespace: dict, *, max_terms: int = _MAX_TERMS) -> dict | None:
    """Probe Trends for the top underexplored niches and return the best one.

    Returns a demand signal dict, or ``None`` when there are no niches to probe
    or every Trends lookup failed (offline, no data, etc.).
    """
    terms = [item["term"] for item in whitespace.get("underexplored_terms", [])][:max_terms]
    if not terms:
        return None

    trends = Trends(client)
    best: dict | None = None
    checked = 0
    for term in terms:
        try:
            results = trends.search(term)
        except Exception:
            continue
        checked += 1
        points = Trends.parse_interest(results)
        growth = Trends.growth(points)
        if growth is None:
            continue
        candidate = {
            "term": term,
            "growth": round(growth, 1),
            "score": round(Trends.demand_score(growth)),
            "note": Trends.note(growth),
        }
        if best is None or candidate["growth"] > best["growth"]:
            best = candidate

    if best is None:
        return None
    best["checked"] = checked
    return best
