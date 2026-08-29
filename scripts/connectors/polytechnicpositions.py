from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://polytechnicpositions.com"
SEARCH_URL = f"{BASE_URL}/announcements,a.html"
MAX_PAGES = 2

_COUNTRY_TO_ISO2 = {
    "australia": "AU",
    "austria": "AT",
    "belgium": "BE",
    "canada": "CA",
    "china": "CN",
    "denmark": "DK",
    "finland": "FI",
    "france": "FR",
    "germany": "DE",
    "hong kong": "HK",
    "india": "IN",
    "ireland": "IE",
    "italy": "IT",
    "japan": "JP",
    "netherlands": "NL",
    "new zealand": "NZ",
    "norway": "NO",
    "saudi arabia": "SA",
    "singapore": "SG",
    "south korea": "KR",
    "spain": "ES",
    "sweden": "SE",
    "switzerland": "CH",
    "united arab emirates": "AE",
    "united kingdom": "GB",
    "united states": "US",
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


def _rank_from_text(text: str) -> str | None:
    value = text.lower()
    if any(
        label in value
        for label in (
            "postdoc",
            "post-doctoral",
            "research fellow",
            "research associate",
            "research assistant",
            "research scientist",
            "researcher",
        )
    ):
        return "postdoc-researcher"
    if any(
        label in value
        for label in (
            "professor",
            "lecturer",
            "faculty position",
            "faculty positions",
            "tenure-track",
            "tenure track",
            "instructor",
        )
    ):
        return "professor-lecture"
    return None


def _field_tags(query: dict[str, Any], text: str) -> list[str]:
    tags: list[str] = []
    field = (query.get("field") or "").strip()
    if field:
        tags.extend(part for part in field.split("/") if part)

    value = text.lower()
    if re.search(r"\b(cs|computer science|computing|informatics|software)\b", value):
        tags.append("computer-science")
    if "machine learning" in value or re.search(r"\bml\b", value):
        tags.append("machine-learning")
    if re.search(r"\bai\b", value) or "artificial intelligence" in value:
        tags.append("ai")
    if "data science" in value:
        tags.append("data-science")
    if "cybersecurity" in value or "cyber security" in value:
        tags.append("cybersecurity")
    if "electrical" in value or "electronic" in value:
        tags.append("electrical-engineering")
    if "engineering" in value:
        tags.append("engineering")
    return sorted(set(tags)) or ["academic"]


def _parse_search_page(html: str, query: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    chunks = re.split(r'(?is)(?=<div[^>]+class="[^"]*\ban-box\b[^"]*"[^>]*>)', html)
    for chunk in chunks:
        title_match = re.search(
            r'(?is)<h1[^>]+class="[^"]*\btitle\b[^"]*"[^>]*>\s*'
            r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
            chunk,
        )
        if not title_match:
            continue

        title = _clean_text(title_match.group("title"))
        if not title:
            continue
        institution_match = re.search(
            r'(?is)<h3[^>]+class="[^"]*\bcompany\b[^"]*"[^>]*>(.*?)</h3>', chunk
        )
        country_match = re.search(
            r'(?is)<div[^>]+class="[^"]*\bcountry\b[^"]*"[^>]*>.*?'
            r'<a[^>]*>(.*?)</a>',
            chunk,
        )
        institution = _clean_text(institution_match.group(1) if institution_match else "")
        country_name = _clean_text(country_match.group(1) if country_match else "")
        combined = f"{title} {institution}"
        results.append(
            {
                "title": title,
                "institution": institution or "Unknown Institution",
                "department": None,
                "location": country_name or None,
                "country": _COUNTRY_TO_ISO2.get(country_name.lower()),
                "rank": _rank_from_text(combined),
                "field_tags": _field_tags(query, combined),
                "employment_type": None,
                "posted_date": None,
                "deadline": None,
                "visa_info": None,
                "salary_range": None,
                "requirements": [],
                "materials": [],
                "url": urljoin(BASE_URL, unescape(title_match.group("href"))),
                "source": "polytechnicpositions",
                "source_type": "specialist-board",
                "language": "en",
            }
        )
    return results


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch public engineering and technology listings from PolytechnicPositions."""
    keywords = (query.get("search_term") or "").strip() or (query.get("field") or "engineering")
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for page in range(MAX_PAGES):
        params = {"q": keywords}
        if page:
            params["start"] = str(page * 10)
        url = f"{SEARCH_URL}?{urlencode(params)}"
        try:
            html = _fetch_text(url)
        except Exception:
            continue

        page_rows = _parse_search_page(html, query)
        if not page_rows:
            break
        for row in page_rows:
            key = str(row["url"])
            if key in seen:
                continue
            seen.add(key)
            results.append(row)

    return results
