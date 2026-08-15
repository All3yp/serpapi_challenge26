"""Google Scholar search and local citation formatting."""

from __future__ import annotations

from dataclasses import dataclass, field

CURRENT_YEAR = 2026

_VENUE_STRIP = " …·,;:"
_YEAR_START = 1900


@dataclass
class Paper:
    title: str
    result_id: str = ""
    snippet: str = ""
    year: int | None = None
    authors: list[str] = field(default_factory=list)
    venue: str = ""
    cited_by: int = 0
    link: str = ""
    pdf: str = ""


class Scholar:
    """Search the ``google_scholar`` engine and normalize results."""

    def __init__(self, client) -> None:
        self.client = client

    def search(
        self,
        q: str,
        *,
        num: int = 20,
        start: int = 0,
        year_low: int | None = None,
        year_high: int | None = None,
        hl: str = "en",
    ):
        params = {"engine": "google_scholar", "q": q, "num": num, "hl": hl}
        if year_low:
            params["as_ylo"] = year_low
        if year_high:
            params["as_yhi"] = year_high
        if start:
            params["start"] = start
        return self.client.search(params)

    @staticmethod
    def parse(results) -> list[Paper]:
        return [Scholar._parse_item(item) for item in results.get("organic_results", [])]

    @staticmethod
    def filter_papers(
        papers: list[Paper],
        *,
        year_low: int | None = None,
        year_high: int | None = None,
        limit: int | None = None,
    ) -> list[Paper]:
        filtered = papers
        if year_low is not None:
            filtered = [paper for paper in filtered if paper.year is None or paper.year >= year_low]
        if year_high is not None:
            filtered = [paper for paper in filtered if paper.year is None or paper.year <= year_high]
        if limit is not None:
            filtered = filtered[:limit]
        return filtered

    @staticmethod
    def _parse_item(item: dict) -> Paper:
        info = item.get("publication_info") or {}
        summary = info.get("summary") or ""
        inline = item.get("inline_links") or {}
        cited = (inline.get("cited_by") or {}).get("total") or 0

        authors = [a["name"] for a in info.get("authors") or [] if a.get("name")]

        return Paper(
            title=item.get("title", ""),
            result_id=item.get("result_id", ""),
            snippet=item.get("snippet", ""),
            year=extract_year(summary) or extract_year(item.get("title", "")),
            authors=authors,
            venue=extract_venue(summary),
            cited_by=int(cited),
            link=item.get("link", ""),
            pdf=_first_pdf(item.get("resources") or []),
        )


def _first_pdf(resources: list[dict]) -> str:
    for resource in resources:
        if (resource.get("file_format") or "").upper() == "PDF":
            return resource.get("link", "")
    return ""


def _scan_years(text: str) -> list[int]:
    years = []
    length = len(text)
    for i in range(length - 3):
        if i > 0 and text[i - 1].isdigit():
            continue
        if i + 4 < length and text[i + 4].isdigit():
            continue
        token = text[i : i + 4]
        if token.isdigit() and _YEAR_START <= int(token) <= CURRENT_YEAR:
            years.append(int(token))
    return years


def extract_year(text: str | None) -> int | None:
    if not text:
        return None
    years = _scan_years(text)
    return max(years) if years else None


def extract_venue(summary: str) -> str:
    if not summary:
        return ""
    parts = [part.strip() for part in summary.split(" - ")]
    venue = parts[1] if len(parts) >= 2 else summary
    return _drop_trailing_year(venue).strip(_VENUE_STRIP)


def _drop_trailing_year(text: str) -> str:
    if len(text) >= 6 and text[-4:].isdigit() and text[-6:-4] == ", ":
        return text[:-6]
    return text


def _author_surname(name: str) -> str:
    return name.split()[-1]


def _author_initials(name: str) -> str:
    return " ".join(f"{token[0]}." for token in name.split()[:-1])


def format_abnt(paper: Paper) -> str:
    authors = "; ".join(
        f"{_author_surname(a).upper()}, {_author_initials(a)}" for a in paper.authors
    )
    year = paper.year or "s.d."
    venue = f" {paper.venue}," if paper.venue else ""
    return f"{authors}. {paper.title}.{venue} {year}."


def _format_author_apa(name: str) -> str:
    return f"{_author_surname(name)}, {_author_initials(name)}"


def format_apa(paper: Paper) -> str:
    if not paper.authors:
        authors = "(s.a.)"
    elif len(paper.authors) == 1:
        authors = _format_author_apa(paper.authors[0])
    else:
        authors = ", ".join(_format_author_apa(a) for a in paper.authors[:-1])
        authors += f", & {_format_author_apa(paper.authors[-1])}"

    year = paper.year or "s.d."
    venue = f" {paper.venue}." if paper.venue else "."
    return f"{authors} ({year}). {paper.title}.{venue}"


_ABNT_STYLES = ("abnt", "nbr", "nbr 6023")


def format_citation(paper: Paper, style: str) -> str:
    if style.strip().lower() in _ABNT_STYLES:
        return format_abnt(paper)
    return format_apa(paper)
