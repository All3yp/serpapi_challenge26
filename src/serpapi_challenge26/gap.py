"""Local gap-analysis signals over a Scholar search result."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .scholar import CURRENT_YEAR, Paper

_OPEN_MARKERS = (
    "future work", "further research", "remains open", "little is known",
    "open problem", "open question", "not yet", "still unclear",
    "remains unclear", "poorly understood", "needs further", "lacks",
    "trabalhos futuros", "pesquisas futuras", "pouco se sabe",
    "questão em aberto", "problema em aberto", "ainda não",
    "permanece em aberto", "pouco explorado", "lacuna", "carece de",
)

_STOPWORDS = frozenset(
    """a an and are as at be by for from in is it of on or that the to with
    com da de do em para por que uma um dos das nos nas e ou mais como entre
    sobre based using via their its our new study data model""".split()
)

_PUNCTUATION = ".,;:()[]{}\"'!?—-–"
_MIN_TERM_LENGTH = 3


@dataclass(frozen=True)
class Thresholds:
    recent_years: int = 3
    stagnant_years: int = 5
    cooling_ratio: float = 0.3
    hot_ratio: float = 0.6
    top3_concentration: float = 0.6
    underexplored_max_papers: int = 2
    underexplored_limit: int = 10
    hot_limit: int = 5
    top_papers_limit: int = 5
    direction_terms_limit: int = 6
    max_score: int = 90

    score_cooling: int = 85
    score_hot: int = 30
    score_steady: int = 55
    score_stagnant_concentrated: int = 80
    score_stagnant: int = 65
    score_healthy: int = 35
    score_neutral: int = 50
    score_whitespace_base: int = 40
    score_whitespace_step: int = 5
    score_open_base: int = 30
    score_open_step: int = 15
    score_open_none: int = 25


THRESHOLDS = Thresholds()


def _is_term(token: str) -> bool:
    return (
        len(token) >= _MIN_TERM_LENGTH
        and token not in _STOPWORDS
        and not token.isdigit()
    )


def _tokens(text: str) -> list[str]:
    tokens = []
    for word in text.split():
        token = word.strip(_PUNCTUATION).lower()
        if _is_term(token):
            tokens.append(token)
    return tokens


@dataclass
class GapReport:
    score: int
    temporal: dict
    whitespace: dict
    stagnation: dict
    open_questions: dict
    directions: list[dict]


class GapAnalyzer:
    def __init__(self, papers: list[Paper]) -> None:
        self.papers = papers

    def analyze(self) -> GapReport:
        temporal = self.temporal_density()
        whitespace = self.subtopic_whitespace()
        stagnation = self.citation_stagnation()
        open_questions = self.open_questions()

        signals = [temporal, whitespace, stagnation, open_questions]
        score = round(sum(signal["score"] for signal in signals) / len(signals))

        return GapReport(
            score=score,
            temporal=temporal,
            whitespace=whitespace,
            stagnation=stagnation,
            open_questions=open_questions,
            directions=self._directions({
                "temporal": temporal,
                "whitespace": whitespace,
                "stagnation": stagnation,
                "open_questions": open_questions,
            }),
        )

    def temporal_density(self) -> dict:
        years = [paper.year for paper in self.papers if paper.year]
        if not years:
            return {"score": THRESHOLDS.score_neutral, "recent_ratio": None, "histogram": {}, "note": "no_years"}

        counts = Counter(years)
        histogram = {str(year): counts[year] for year in sorted(counts)}
        recent = sum(1 for year in years if year >= CURRENT_YEAR - THRESHOLDS.recent_years)
        ratio = recent / len(years)

        if ratio < THRESHOLDS.cooling_ratio:
            score, note = THRESHOLDS.score_cooling, "cooling"
        elif ratio > THRESHOLDS.hot_ratio:
            score, note = THRESHOLDS.score_hot, "hot"
        else:
            score, note = THRESHOLDS.score_steady, "steady"

        return {
            "score": score,
            "recent_ratio": round(ratio, 2),
            "histogram": histogram,
            "note": note,
        }

    def subtopic_whitespace(self) -> dict:
        term_papers: dict[str, set[int]] = defaultdict(set)
        term_cites: dict[str, list[int]] = defaultdict(list)

        for index, paper in enumerate(self.papers):
            for term in set(_tokens(paper.title)):
                term_papers[term].add(index)
                term_cites[term].append(paper.cited_by)

        stats = []
        for term, paper_indexes in term_papers.items():
            cites = term_cites[term]
            stats.append({
                "term": term,
                "papers": len(paper_indexes),
                "avg_cites": round(sum(cites) / len(cites), 1),
            })

        stats.sort(key=lambda stat: (stat["papers"], stat["avg_cites"]))
        underexplored = [
            stat for stat in stats if stat["papers"] <= THRESHOLDS.underexplored_max_papers
        ][:THRESHOLDS.underexplored_limit]
        hot = sorted(stats, key=lambda stat: (-stat["papers"], -stat["avg_cites"]))[:THRESHOLDS.hot_limit]

        score = min(
            THRESHOLDS.max_score,
            THRESHOLDS.score_whitespace_base + len(underexplored) * THRESHOLDS.score_whitespace_step,
        )
        if not underexplored:
            score = THRESHOLDS.score_whitespace_base

        return {"score": score, "underexplored_terms": underexplored, "hot_terms": hot}

    def citation_stagnation(self) -> dict:
        cited = [paper for paper in self.papers if paper.cited_by > 0]
        if not cited:
            return {"score": THRESHOLDS.score_neutral, "note": "no_citations", "top_papers": []}

        top = sorted(cited, key=lambda paper: -paper.cited_by)[:THRESHOLDS.top_papers_limit]
        top_years = [paper.year for paper in top if paper.year]
        avg_year = sum(top_years) / len(top_years) if top_years else None

        total_cites = sum(paper.cited_by for paper in self.papers)
        top3_cites = sum(paper.cited_by for paper in top[:3])
        top3_share = top3_cites / total_cites if total_cites else 0

        stagnant = avg_year is not None and avg_year <= CURRENT_YEAR - THRESHOLDS.stagnant_years
        concentrated = top3_share >= THRESHOLDS.top3_concentration

        if stagnant and concentrated:
            score, note = THRESHOLDS.score_stagnant_concentrated, "stagnant_concentrated"
        elif stagnant:
            score, note = THRESHOLDS.score_stagnant, "stagnant"
        else:
            score, note = THRESHOLDS.score_healthy, "healthy"

        return {
            "score": score,
            "avg_top_year": round(avg_year, 1) if avg_year else None,
            "top3_share": round(top3_share, 2),
            "note": note,
            "top_papers": [
                {"title": paper.title, "cited_by": paper.cited_by, "year": paper.year}
                for paper in top
            ],
        }

    def open_questions(self) -> dict:
        found = []
        for paper in self.papers:
            text = f"{paper.title} {paper.snippet}".lower()
            markers = [marker for marker in _OPEN_MARKERS if marker in text]
            if markers:
                found.append({"title": paper.title, "markers": markers, "year": paper.year})

        score = THRESHOLDS.score_open_none
        if found:
            score = min(THRESHOLDS.max_score, THRESHOLDS.score_open_base + len(found) * THRESHOLDS.score_open_step)
        return {"score": score, "count": len(found), "papers": found}

    @staticmethod
    def _directions(signals: dict) -> list[dict]:
        temporal = signals["temporal"]
        whitespace = signals["whitespace"]
        stagnation = signals["stagnation"]
        open_questions = signals["open_questions"]

        directions: list[dict] = []

        if whitespace["underexplored_terms"]:
            terms = ", ".join(
                item["term"] for item in whitespace["underexplored_terms"][:THRESHOLDS.direction_terms_limit]
            )
            directions.append({"id": "underexplored", "terms": terms})

        if stagnation["note"].startswith("stagnant"):
            directions.append({"id": "stagnant"})

        if temporal["note"] == "cooling":
            directions.append({"id": "cooling"})

        if open_questions["count"]:
            directions.append({"id": "open_questions", "count": open_questions["count"]})

        if not directions:
            directions.append({"id": "saturated"})

        return directions
