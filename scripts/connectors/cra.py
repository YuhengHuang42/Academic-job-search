from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import Any
from urllib.request import Request, urlopen

BASE_URL = "https://careercenter.cra.org"

_COUNTRY_TO_ISO2 = {
    "united states": "US",
    "usa": "US",
    "canada": "CA",
    "united kingdom": "GB",
    "uk": "GB",
    "germany": "DE",
    "france": "FR",
    "japan": "JP",
    "singapore": "SG",
    "united arab emirates": "AE",
    "australia": "AU",
}


def _fetch_text(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; academic-job-search-mcp/0.1)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def _clean_text(html_fragment: str | None) -> str:
    if not html_fragment:
        return ""
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", html_fragment))).strip()


def _posted_to_iso(posted: str | None) -> str | None:
    if not posted:
        return None
    try:
        return datetime.strptime(posted.strip(), "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def _rank_from_text(text: str) -> str | None:
    t = text.lower()
    if "postdoc" in t or "postdoctoral" in t or "research scientist" in t or "researcher" in t:
        return "postdoc-researcher"
    if (
        "professor" in t
        or "lecturer" in t
        or "instructor" in t
        or "assistant teaching professor" in t
        or "tenure-track" in t
    ):
        return "professor-lecture"
    return None


def _field_tags(query: dict[str, Any], text: str) -> list[str]:
    tags: list[str] = []
    field = (query.get("field") or "").strip()
    if field:
        tags.extend([x for x in field.split("/") if x])
    t = text.lower()
    if re.search(r"\b(cs|computer science|computing|informatics|software)\b", t):
        tags.append("computer-science")
    if "machine learning" in t or re.search(r"\bml\b", t):
        tags.append("machine-learning")
    if re.search(r"\bai\b", t) or "artificial intelligence" in t:
        tags.append("ai")
    if "security" in t or "cryptography" in t or "privacy" in t:
        tags.append("security-privacy")
    return sorted(set(tags)) or ["academic"]


def _country_from_location(location: str | None) -> str | None:
    if not location:
        return None
    # Many cards expose "City, State/Country". Use the trailing component.
    candidate = location.split(",")[-1].strip().lower()
    return _COUNTRY_TO_ISO2.get(candidate)


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse featured public listings from CRA Career Center."""
    try:
        html = _fetch_text(BASE_URL)
    except Exception:
        return []

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    card_pattern = re.compile(
        r"(?is)<h3[^>]*>\s*([^<].*?)\s*</h3>.*?"
        r"<h4[^>]*>\s*([^<].*?)\s*</h4>.*?"
        r"<h4[^>]*>\s*([^<].*?)\s*</h4>.*?"
        r".*?Posted\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})"
    )

    for title_raw, institution_raw, location_raw, posted_raw in card_pattern.findall(html):
        title = _clean_text(title_raw)
        institution = _clean_text(institution_raw)
        location = _clean_text(location_raw)
        posted_text = _clean_text(posted_raw)
        if not title:
            continue
        key = f"{title.lower()}::{institution.lower()}::{location.lower()}::{posted_text}"
        if key in seen:
            continue
        seen.add(key)
        combined = f"{title} {institution}"
        results.append(
            {
                "title": title,
                "institution": institution or "Unknown Institution",
                "department": None,
                "location": location or None,
                "country": _country_from_location(location),
                "rank": _rank_from_text(combined),
                "field_tags": _field_tags(query, combined),
                "employment_type": None,
                "posted_date": _posted_to_iso(posted_text),
                "deadline": None,
                "visa_info": None,
                "salary_range": None,
                "requirements": [],
                "materials": [],
                "url": BASE_URL,
                "source": "cra",
                "source_type": "society",
                "language": "en",
            }
        )

    return results
