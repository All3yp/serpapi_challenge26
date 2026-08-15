"""Google Scholar search and local citation formatting."""

from __future__ import annotations

from dataclasses import dataclass, field

CURRENT_YEAR = 2026

_VENUE_STRIP = " …·,;:"
_YEAR_START = 1900

_PARTICLES = frozenset({"da", "de", "do", "das", "dos", "e", "del", "van", "von"})
_PAGE_SIZE = 20
_MAX_PAGES = 50


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

    def search_all(
        self,
        q: str,
        *,
        max_results: int = 20,
        hl: str = "en",
        year_low: int | None = None,
        year_high: int | None = None,
    ) -> list[Paper]:
        papers: list[Paper] = []
        start = 0
        pages = 0
        while len(papers) < max_results and pages < _MAX_PAGES:
            page = self.search(
                q,
                num=_PAGE_SIZE,
                start=start,
                hl=hl,
                year_low=year_low,
                year_high=year_high,
            )
            batch = self.parse(page)
            pages += 1
            if not batch:
                break
            papers.extend(batch)
            start += _PAGE_SIZE
            if not self._has_next(page):
                break
        return papers[:max_results]

    @staticmethod
    def _has_next(results) -> bool:
        serpapi_next = (results.get("serpapi_pagination") or {}).get("next")
        scholar_next = (results.get("pagination") or {}).get("next")
        return bool(serpapi_next or scholar_next)

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
        cited = _coerce_int((inline.get("cited_by") or {}).get("total"))

        authors = [a["name"] for a in info.get("authors") or [] if a.get("name")]

        return Paper(
            title=item.get("title", ""),
            result_id=item.get("result_id", ""),
            snippet=item.get("snippet", ""),
            year=extract_year(summary) or extract_year(item.get("title", "")),
            authors=authors,
            venue=extract_venue(summary),
            cited_by=cited,
            link=item.get("link", ""),
            pdf=_first_pdf(item.get("resources") or []),
        )


def _coerce_int(value) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0


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


def _author_given(name: str) -> str:
    return " ".join(name.split()[:-1])


def _author_surname(name: str) -> str:
    return name.split()[-1]


def _author_initials(name: str) -> str:
    tokens = name.split()[:-1]
    initials = [f"{token[0]}." for token in tokens if token and token.lower() not in _PARTICLES]
    return " ".join(initials)


def _surname_given(name: str) -> str:
    """``Surname, Given`` (bibliography-style inversion); mononyms stay bare."""
    given = _author_given(name)
    surname = _author_surname(name)
    return f"{surname}, {given}" if given else surname


def _given_surname(name: str) -> str:
    """``Given Surname`` (natural order); mononyms stay bare."""
    given = _author_given(name)
    surname = _author_surname(name)
    return f"{given} {surname}" if given else surname


def format_abnt(paper: Paper) -> str:
    authors = "; ".join(_format_author_abnt(a) for a in paper.authors)
    year = paper.year or "s.d."
    venue = f" {paper.venue}," if paper.venue else ""
    prefix = f"{authors} " if authors else ""
    return f"{prefix}{paper.title}.{venue} {year}."


def _format_author_abnt(name: str) -> str:
    surname = _author_surname(name)
    initials = _author_initials(name)
    return f"{surname.upper()}, {initials}".rstrip(", ")


def _format_author_apa(name: str) -> str:
    surname = _author_surname(name)
    initials = _author_initials(name)
    return f"{surname}, {initials}".rstrip(", ")


def format_apa(paper: Paper) -> str:
    if not paper.authors:
        authors = "(s.a.)"
    elif len(paper.authors) == 1:
        authors = _format_author_apa(paper.authors[0])
    else:
        authors = ", ".join(_format_author_apa(a) for a in paper.authors[:-1])
        authors += f", & {_format_author_apa(paper.authors[-1])}"

    year = paper.year or "s.d."
    venue = f" {paper.venue}." if paper.venue else ""
    return f"{authors} ({year}). {paper.title}.{venue}"


def _format_author_ieee(name: str) -> str:
    surname = _author_surname(name)
    initials = _author_initials(name)
    return f"{initials} {surname}".strip()


def format_ieee(paper: Paper) -> str:
    if not paper.authors:
        authors = ""
    elif len(paper.authors) == 1:
        authors = _format_author_ieee(paper.authors[0])
    elif len(paper.authors) == 2:
        authors = (
            f"{_format_author_ieee(paper.authors[0])} and "
            f"{_format_author_ieee(paper.authors[1])}"
        )
    else:
        authors = ", ".join(_format_author_ieee(a) for a in paper.authors[:-1])
        authors += f", and {_format_author_ieee(paper.authors[-1])}"

    year = str(paper.year) if paper.year else "n.d."
    title = f'"{paper.title},"'
    venue = f" {paper.venue}," if paper.venue else ""
    prefix = f"{authors}, " if authors else ""
    return f"{prefix}{title}{venue} {year}."


_BIBTEX_ESCAPES = {
    "\\": "\\\\",
    "{": "\\{",
    "}": "\\}",
    "&": "\\&",
    "%": "\\%",
    "#": "\\#",
    "_": "\\_",
}


def _bibtex_escape(text: str) -> str:
    return "".join(_BIBTEX_ESCAPES.get(ch, ch) for ch in text)


def _bibtex_key(paper: Paper) -> str:
    surname = _author_surname(paper.authors[0]).lower() if paper.authors else ""
    year = str(paper.year) if paper.year else ""
    title_token = (paper.title or "paper").split()[0].lower()
    key = "".join(ch for ch in f"{surname}{year}{title_token}" if ch.isalnum())
    return key or "paper"


def _bibtex_author(name: str) -> str:
    return _surname_given(name)


def format_bibtex(paper: Paper) -> str:
    key = _bibtex_key(paper)
    lines = [f"@article{{{key},"]
    if paper.authors:
        authors = " and ".join(_bibtex_author(a) for a in paper.authors)
        lines.append(f"  author = {{{_bibtex_escape(authors)}}},")
    lines.append(f"  title = {{{_bibtex_escape(paper.title)}}},")
    if paper.year:
        lines.append(f"  year = {{{paper.year}}},")
    if paper.venue:
        lines.append(f"  journal = {{{_bibtex_escape(paper.venue)}}},")
    if paper.link:
        lines.append(f"  url = {{{_bibtex_escape(paper.link)}}},")
    lines.append("}")
    return "\n".join(lines)


def format_vancouver(paper: Paper) -> str:
    if paper.authors:
        names = [_format_author_vancouver(a) for a in paper.authors[:6]]
        authors = ", ".join(names)
        if len(paper.authors) > 6:
            authors += ", et al"
        authors += ". "
    else:
        authors = ""

    title = f"{paper.title}. " if paper.title else ""
    venue = f"{paper.venue}. " if paper.venue else ""
    year = str(paper.year) if paper.year else ""
    return f"{authors}{title}{venue}{year}".rstrip()


def _format_author_vancouver(name: str) -> str:
    surname = _author_surname(name)
    given = _author_given(name)
    initials = "".join(
        f"{token[0]}" for token in given.split()
        if token and token.lower() not in _PARTICLES
    )
    return f"{surname} {initials}".strip()


def format_mla(paper: Paper) -> str:
    if not paper.authors:
        authors = ""
    elif len(paper.authors) == 1:
        authors = _surname_given(paper.authors[0])
    elif len(paper.authors) == 2:
        first = paper.authors[0]
        second = paper.authors[1]
        authors = f"{_surname_given(first)}, and {_given_surname(second)}"
    else:
        authors = f"{_surname_given(paper.authors[0])}, et al"

    year = str(paper.year) if paper.year else "n.d."
    title = f'"{paper.title}."'
    venue = f" {paper.venue}," if paper.venue else ""
    prefix = f"{authors}. " if authors else ""
    return f"{prefix}{title}{venue} {year}."


def format_chicago(paper: Paper) -> str:
    if not paper.authors:
        authors = ""
    else:
        authors = ", ".join(_surname_given(a) for a in paper.authors)

    year = str(paper.year) if paper.year else "n.d."
    title = f'"{paper.title}."'
    venue = f" {paper.venue}." if paper.venue else ""
    prefix = f"{authors}. " if authors else ""
    return f"{prefix}{year}. {title}{venue}".strip()


_ABNT_STYLES = ("abnt", "nbr", "nbr 6023")
_IEEE_STYLES = ("ieee",)
_BIBTEX_STYLES = ("bibtex", "bib")
_VANCOUVER_STYLES = ("vancouver", "icmje")
_MLA_STYLES = ("mla",)
_CHICAGO_STYLES = ("chicago",)


def format_citation(paper: Paper, style: str) -> str:
    normalized = style.strip().lower()
    if normalized in _ABNT_STYLES:
        return format_abnt(paper)
    if normalized in _IEEE_STYLES:
        return format_ieee(paper)
    if normalized in _BIBTEX_STYLES:
        return format_bibtex(paper)
    if normalized in _VANCOUVER_STYLES:
        return format_vancouver(paper)
    if normalized in _MLA_STYLES:
        return format_mla(paper)
    if normalized in _CHICAGO_STYLES:
        return format_chicago(paper)
    return format_apa(paper)
