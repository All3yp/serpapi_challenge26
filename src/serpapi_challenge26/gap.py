"""Local gap-analysis signals over a Scholar search result."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .scholar import CURRENT_YEAR, Paper

_OPEN_MARKERS = (
    "future work", "further research", "further investigation", "further study",
    "future research", "future directions", "more research", "remains open",
    "little is known", "little attention", "open problem", "open question",
    "open challenge", "research gap", "not yet", "still unclear",
    "remains unclear", "remains to be", "has not been", "poorly understood",
    "needs further", "lacks", "unexplored", "underexplored", "understudied",
    "trabalhos futuros", "pesquisas futuras", "pesquisas adicionais",
    "direções futuras", "investigação futura", "pouco se sabe", "pouca atenção",
    "pouco estudado", "questão em aberto", "problema em aberto", "ainda não",
    "permanece em aberto", "pouco explorado", "lacuna", "lacuna de pesquisa",
    "carece de",
)

_STOPWORDS = frozenset(
    """a an and are as at be by for from in is it of on or that the to with
    com da de do em para por que uma um dos das nos nas e ou mais como entre
    sobre based using via their its our new study data model
    what do we want whom when how why which who where this these those
    into beyond without between during""".split()
)

# Structural/academic boilerplate that never denotes a subtopic. These are
# excluded so "underexplored" surfaces domain concepts, not article types.
_GENERIC_TERMS = frozenset(
    """review reviews survey surveys systematic analysis analyses approach
    approaches application applications method methods methodology framework
    frameworks technique techniques algorithm algorithms model models system
    systems toward towards state art current recent existing novel studies
    research literature overview perspective case challenge challenges
    opportunity opportunities future directions advances trend trends
    comparative comprehensive structured empirical theoretical practical
    concept concepts principle principles status quo fundamentals""".split()
)

_PUNCTUATION = ".,;:()[]{}\"'!?—-–"
_MIN_TERM_LENGTH = 3
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_SENTENCE_MAX_WORDS = 60


@dataclass(frozen=True)
class Thresholds:
    recent_years: int = 3
    stagnant_years: int = 5
    cooling_ratio: float = 0.3
    hot_ratio: float = 0.6
    top3_concentration: float = 0.6
    underexplored_max_papers: int = 2
    underexplored_max_avg_cites: float = 200.0
    hot_limit: int = 10
    top_for_metrics: int = 5
    max_score: int = 100

    score_cooling: int = 85
    score_hot: int = 30
    score_steady: int = 55
    score_stagnant_concentrated: int = 80
    score_stagnant: int = 65
    score_healthy: int = 35
    score_neutral: int = 50
    score_whitespace_base: int = 40
    score_whitespace_step: int = 5

    # Explicit tiers for the open-questions signal.
    open_many_threshold: int = 3
    open_tier_many: int = 100
    open_tier_some: int = 75
    open_tier_one: int = 45
    open_tier_none: int = 25

    # Weights for the weighted average of the four signal scores.
    weight_temporal: float = 0.35
    weight_whitespace: float = 0.25
    weight_stagnation: float = 0.25
    weight_open: float = 0.15


THRESHOLDS = Thresholds()


def _is_term(token: str) -> bool:
    return (
        len(token) >= _MIN_TERM_LENGTH
        and token not in _STOPWORDS
        and token not in _GENERIC_TERMS
        and token.isalpha()
    )


def _tokens(text: str) -> list[str]:
    tokens = []
    for word in text.split():
        token = word.strip(_PUNCTUATION).lower()
        if _is_term(token):
            tokens.append(token)
    return tokens


def _phrases(text: str) -> list[str]:
    """Content-bearing unigrams + bigrams from a title.

    Bigrams capture multi-word subtopics (``drug discovery``) that unigrams
    alone miss; unigrams are the fallback when a concept is a single word.
    """
    tokens = _tokens(text)
    phrases = list(tokens)
    phrases.extend(f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1))
    return phrases


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

        weighted = (
            temporal["score"] * THRESHOLDS.weight_temporal
            + whitespace["score"] * THRESHOLDS.weight_whitespace
            + stagnation["score"] * THRESHOLDS.weight_stagnation
            + open_questions["score"] * THRESHOLDS.weight_open
        )
        score = round(weighted)

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
        phrase_papers: dict[str, set[int]] = defaultdict(set)
        phrase_cites: dict[str, list[int]] = defaultdict(list)

        for index, paper in enumerate(self.papers):
            for phrase in set(_phrases(paper.title)):
                phrase_papers[phrase].add(index)
                phrase_cites[phrase].append(paper.cited_by)

        stats = []
        for phrase, paper_indexes in phrase_papers.items():
            cites = phrase_cites[phrase]
            stats.append({
                "term": phrase,
                "papers": len(paper_indexes),
                "avg_cites": round(sum(cites) / len(cites), 1),
            })

        underexplored = sorted(
            [
                stat for stat in stats
                if stat["papers"] <= THRESHOLDS.underexplored_max_papers
                and stat["avg_cites"] <= THRESHOLDS.underexplored_max_avg_cites
            ],
            key=lambda stat: (stat["papers"], stat["avg_cites"]),
        )
        hot = sorted(stats, key=lambda stat: (-stat["papers"], -stat["avg_cites"]))[:THRESHOLDS.hot_limit]

        score = THRESHOLDS.score_whitespace_base
        if underexplored:
            score = min(
                THRESHOLDS.max_score,
                THRESHOLDS.score_whitespace_base + len(underexplored) * THRESHOLDS.score_whitespace_step,
            )

        return {"score": score, "underexplored_terms": underexplored, "hot_terms": hot}

    def citation_stagnation(self) -> dict:
        cited = sorted(
            [paper for paper in self.papers if paper.cited_by > 0],
            key=lambda paper: -paper.cited_by,
        )
        if not cited:
            return {"score": THRESHOLDS.score_neutral, "note": "no_citations", "top_papers": []}

        top = cited[:THRESHOLDS.top_for_metrics]
        top_years = [paper.year for paper in top if paper.year]
        avg_year = sum(top_years) / len(top_years) if top_years else None

        total_cites = sum(paper.cited_by for paper in self.papers)
        top3_cites = sum(paper.cited_by for paper in cited[:3])
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
                for paper in cited
            ],
        }

    @staticmethod
    def _open_sentences(text: str) -> list[tuple[str, str]]:
        """Return ``(marker, sentence)`` for each sentence declaring an open gap.

        A marker is a canonical, translatable key; the sentence is the verbatim
        excerpt (from title or snippet) so the user can verify the claim.
        """
        sentences = _SENTENCE_END.split(text)
        spans: list[tuple[str, str]] = []
        for sentence in sentences:
            words = sentence.split()
            if not words or len(words) > _SENTENCE_MAX_WORDS:
                continue
            sentence_lower = sentence.lower()
            for marker in _OPEN_MARKERS:
                if marker in sentence_lower:
                    spans.append((marker, sentence.strip()))
                    break
        return spans

    def open_questions(self) -> dict:
        found: list[dict] = []
        total_spans = 0
        for paper in self.papers:
            title_spans = self._open_sentences(paper.title)
            snippet_spans = self._open_sentences(paper.snippet)
            spans = title_spans + snippet_spans
            if not spans:
                continue
            total_spans += len(spans)
            markers = list(dict.fromkeys(marker for marker, _ in spans))
            found.append({
                "title": paper.title,
                "markers": markers,
                "year": paper.year,
                "quotes": [quote for _, quote in spans],
            })

        if len(found) >= THRESHOLDS.open_many_threshold:
            score = THRESHOLDS.open_tier_many
        elif len(found) == 1 and total_spans == 1:
            score = THRESHOLDS.open_tier_one
        elif found:
            score = THRESHOLDS.open_tier_some
        else:
            score = THRESHOLDS.open_tier_none

        return {
            "score": score,
            "count": len(found),
            "papers": found,
            "declarations": total_spans,
        }

    @staticmethod
    def _directions(signals: dict) -> list[dict]:
        temporal = signals["temporal"]
        whitespace = signals["whitespace"]
        stagnation = signals["stagnation"]
        open_questions = signals["open_questions"]

        directions: list[dict] = []

        if whitespace["underexplored_terms"]:
            terms = ", ".join(item["term"] for item in whitespace["underexplored_terms"])
            directions.append({"id": "underexplored", "terms": terms})

        if stagnation["note"].startswith("stagnant"):
            directions.append({"id": "stagnant"})

        if temporal["note"] == "cooling":
            directions.append({"id": "cooling"})

        if open_questions["count"]:
            directions.append({
                "id": "open_questions",
                "count": open_questions["count"],
                "titles": [paper["title"] for paper in open_questions["papers"]],
            })

        if not directions:
            directions.append({"id": "saturated"})

        return directions
