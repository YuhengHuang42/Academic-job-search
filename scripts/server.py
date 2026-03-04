from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from connectors import academicjobsonline, academicwork, cra, jrecin, linkedin
# mcporter --config skills/academic-job-search/scripts/config/mcporter.json list academic-jobs --schema
mcp = FastMCP("academic-job-search")

VALID_SOURCES = {"academicjobsonline", "academicwork", "cra", "jrecin", "linkedin"}
CANONICAL_RANKS = {
    "professor-lecture",
    "postdoc-researcher",
}
RANK_ALIASES = {
    "assistant-professor": "professor-lecture",
    "associate-professor": "professor-lecture",
    "full-professor": "professor-lecture",
    "lecturer": "professor-lecture",
    "postdoc": "postdoc-researcher",
    "research-scientist": "postdoc-researcher",
}
VALID_RANKS = CANONICAL_RANKS | set(RANK_ALIASES.keys())


def _error(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "retryable": retryable}}


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _contains(haystack: str | None, needle: str | None) -> bool:
    if not needle:
        return True
    if not haystack:
        return False
    # Normalize separators and punctuation so "computer science", "computer-science",
    # and "computer_science" are treated as equivalent search strings.
    norm_haystack = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in haystack.lower())
    norm_haystack = " ".join(norm_haystack.replace("-", " ").replace("_", " ").split())
    norm_needle = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in needle.lower())
    norm_needle = " ".join(norm_needle.replace("-", " ").replace("_", " ").split())
    return norm_needle in norm_haystack


def _normalize_rank(rank: str | None) -> str | None:
    if not rank:
        return None
    return RANK_ALIASES.get(rank, rank)


def _record_matches(rec: dict[str, Any], query: dict[str, Any]) -> bool:
    # Search term is treated as a soft preference (for scoring), not a hard filter.
    # This keeps recall high for sparse faculty markets.
    rank = _normalize_rank(query.get("rank"))
    rec_rank = _normalize_rank(rec.get("rank"))
    if rank and rec_rank != rank:
        return False

    location = query.get("location")
    if location and not _contains(rec.get("location"), location):
        return False

    country = query.get("country")
    if country and str(rec.get("country", "")).upper() != str(country).upper():
        return False

    if query.get("is_remote") and not _contains(rec.get("location"), "remote"):
        return False

    deadline_before = _parse_iso_date(query.get("deadline_before"))
    deadline = _parse_iso_date(rec.get("deadline"))
    if deadline_before and deadline and deadline > deadline_before:
        return False

    posted_within_days = query.get("posted_within_days")
    posted_date = _parse_iso_date(rec.get("posted_date"))
    if posted_within_days and posted_date:
        age = (date.today() - posted_date).days
        if age > int(posted_within_days):
            return False

    if query.get("language_hint") in {"en", "ja"}:
        if rec.get("language") and rec["language"] != query["language_hint"]:
            return False

    return True


def _score_record(rec: dict[str, Any], query: dict[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    # 40% query relevance
    q = (query.get("search_term") or "").strip()
    if q and (_contains(rec.get("title"), q) or _contains(" ".join(rec.get("field_tags") or []), q)):
        score += 40
        reasons.append("query match")
    else:
        score += 15

    # 25% rank + field alignment
    rank = _normalize_rank(query.get("rank"))
    rec_rank = _normalize_rank(rec.get("rank"))
    if rank and rec_rank == rank:
        score += 25
        reasons.append("rank match")
    elif not rank:
        score += 12

    # 20% deadline urgency/recency
    deadline = _parse_iso_date(rec.get("deadline"))
    if deadline:
        days_left = (deadline - date.today()).days
        if days_left < 0:
            score += 2
            reasons.append("deadline passed")
        elif days_left <= 14:
            score += 20
            reasons.append("deadline soon")
        else:
            score += 12
    else:
        score += 6
        reasons.append("deadline unknown")

    # 15% hard constraints
    hard = 0
    if query.get("location") and _contains(rec.get("location"), query["location"]):
        hard += 5
    if query.get("country") and str(rec.get("country", "")).upper() == str(query["country"]).upper():
        hard += 5
    if query.get("is_remote") and _contains(rec.get("location"), "remote"):
        hard += 5
    if not any(query.get(k) for k in ("location", "country", "is_remote")):
        hard += 7
    score += min(hard, 15)

    # source priors
    implied_japan = _contains(query.get("location"), "japan") or str(query.get("country", "")).upper() == "JP"
    if implied_japan and rec.get("source") == "jrecin":
        score += 3
        reasons.append("japan-prior source")
    if not implied_japan and rec.get("source") == "academicjobsonline":
        score += 2

    # linkedin is treated as aggregator unless verified institution url exists.
    if rec.get("source") == "linkedin" and rec.get("source_type") == "aggregator":
        score -= 2

    bounded = max(0, min(int(round(score)), 100))
    return float(bounded), reasons


def _dedupe_key(rec: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(rec.get("institution", "")).strip().lower(),
        str(rec.get("title", "")).strip().lower(),
        str(rec.get("location", "")).strip().lower(),
        str(rec.get("deadline", "")).strip().lower(),
    )


@mcp.tool()
def search_academic_jobs(
    search_term: str,
    field: str | None = None,
    rank: str | None = None,
    location: str | None = None,
    country: str | None = None,
    is_remote: bool = False,
    visa_needed: bool | None = None,
    deadline_before: str | None = None,
    posted_within_days: int | None = None,
    sources: list[str] | None = None,
    language_hint: str = "auto",
    max_results: int = 15,
    offset: int = 0,
    verbose: int = 1,
) -> dict[str, Any]:
    if not search_term.strip():
        return _error("INVALID_ARGUMENT", "search_term is required")

    if rank and rank not in VALID_RANKS:
        return _error("INVALID_ARGUMENT", f"rank must be one of: {sorted(VALID_RANKS)}")

    if language_hint not in {"auto", "en", "ja"}:
        return _error("INVALID_ARGUMENT", "language_hint must be auto|en|ja")

    if max_results < 1 or max_results > 200:
        return _error("INVALID_ARGUMENT", "max_results must be between 1 and 200")

    requested_sources = sources or ["academicjobsonline", "academicwork", "cra", "jrecin", "linkedin"]
    invalid = [s for s in requested_sources if s not in VALID_SOURCES]
    if invalid:
        return _error("INVALID_ARGUMENT", f"unsupported sources: {invalid}")

    query: dict[str, Any] = {
        "search_term": search_term,
        "field": field,
        "rank": _normalize_rank(rank),
        "location": location,
        "country": country,
        "is_remote": is_remote,
        "visa_needed": visa_needed,
        "deadline_before": deadline_before,
        "posted_within_days": posted_within_days,
        "language_hint": language_hint,
    }

    source_impl = {
        "academicjobsonline": academicjobsonline.search,
        "academicwork": academicwork.search,
        "cra": cra.search,
        "jrecin": jrecin.search,
        "linkedin": linkedin.search,
    }

    warnings: list[str] = []
    raw: list[dict[str, Any]] = []
    for source in requested_sources:
        try:
            rows = source_impl[source](query)
            raw.extend(rows)
            if source == "linkedin" and not rows:
                warnings.append(
                    "linkedin connector returned 0 rows. Configure a compliant provider/API for production use."
                )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"source {source} failed: {exc}")

    total_found = len(raw)
    matched = [r for r in raw if _record_matches(r, query)]

    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for rec in matched:
        key = _dedupe_key(rec)
        if key not in deduped:
            deduped[key] = rec
    unique_results = list(deduped.values())

    scored: list[dict[str, Any]] = []
    for rec in unique_results:
        fit_score, fit_reasons = _score_record(rec, query)
        row = dict(rec)
        row["id"] = row.get("id") or f"{row.get('source','src')}::{abs(hash(row.get('url', '')))}"
        row["fit_score"] = fit_score
        row["fit_reasons"] = fit_reasons
        scored.append(row)

    scored.sort(key=lambda x: (x.get("fit_score", 0), x.get("deadline") or "9999-99-99"), reverse=True)
    sliced = scored[offset : offset + max_results]

    if visa_needed:
        warnings.append("visa_needed was requested; verify sponsorship directly from posting text.")
    if verbose >= 2 and not sliced:
        warnings.append("No rows matched current filters; try relaxing rank/location/deadline filters.")

    return {
        "query": {
            "search_term": search_term,
            "field": field,
            "rank": query.get("rank"),
        },
        "results": sliced,
        "meta": {
            "total_found": total_found,
            "returned": len(sliced),
            "deduplicated": max(0, len(matched) - len(unique_results)),
            "sources_used": requested_sources,
            "warnings": warnings,
        },
    }


@mcp.tool()
def get_supported_academic_sources() -> dict[str, Any]:
    return {
        "sources": [
            {
                "name": "academicjobsonline",
                "category": "official-board",
                "regions": ["global"],
                "languages": ["en"],
                "notes": "Strong faculty/postdoc signal with clear deadlines.",
            },
            {
                "name": "academicwork",
                "category": "official-board",
                "regions": ["canada", "international"],
                "languages": ["en", "fr"],
                "notes": "CAUT board with strong Canadian higher-ed coverage.",
            },
            {
                "name": "jrecin",
                "category": "official-board",
                "regions": ["japan", "global"],
                "languages": ["ja", "en"],
                "notes": "Japan-focused research and higher-ed listings with rich rank taxonomy.",
            },
            {
                "name": "cra",
                "category": "society",
                "regions": ["global"],
                "languages": ["en"],
                "notes": "CRA career center with computing research and faculty postings.",
            },
            {
                "name": "linkedin",
                "category": "aggregator",
                "regions": ["global"],
                "languages": ["en", "other"],
                "notes": "Broad coverage; verify official institution source when possible.",
            },
        ]
    }


@mcp.tool()
def get_academic_search_tips() -> dict[str, Any]:
    return {
        "tips": [
            "Start with 10-20 results and refine from fit gaps.",
            "Specify rank and region early to reduce noisy matches.",
            "Treat missing visa/deadline fields as unknown, not negative.",
            "Prioritize official-board postings over reposts when duplicates exist.",
        ],
        "examples": [
            {
                "label": "Japan postdoc search",
                "query": {
                    "search_term": "quantum computing",
                    "rank": "postdoc-researcher",
                    "country": "JP",
                    "sources": ["jrecin", "linkedin"],
                    "max_results": 20,
                },
            },
            {
                "label": "Global assistant professor search",
                "query": {
                    "search_term": "computer science",
                    "rank": "professor-lecture",
                    "sources": ["academicjobsonline", "academicwork", "linkedin"],
                    "max_results": 20,
                },
            },
        ],
    }


if __name__ == "__main__":
    mcp.run()
