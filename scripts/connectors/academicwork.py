from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import Any
from urllib.request import Request, urlopen

BASE_URL = "https://www.academicwork.ca/"
MAX_PAGES = 3


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
    if "postdoc" in t or "postdoctoral" in t or "researcher" in t or "research scientist" in t:
        return "postdoc-researcher"
    if "professor" in t or "lecturer" in t or "instructor" in t or "tenure-track" in t:
        return "professor-lecture"
    return None


def _field_tags(query: dict[str, Any], text: str) -> list[str]:
    tags: list[str] = []
    field = (query.get("field") or "").strip()
    if field:
        tags.extend([x for x in field.split("/") if x])
    t = text.lower()
    if re.search(r"\b(cs|computer science|informatics|software|programming)\b", t):
        tags.append("computer-science")
    if "machine learning" in t or re.search(r"\bml\b", t):
        tags.append("machine-learning")
    if re.search(r"\bai\b", t) or "artificial intelligence" in t:
        tags.append("ai")
    return sorted(set(tags)) or ["academic"]


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse public academic listings from academicwork.ca."""
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    article_pattern = re.compile(r"(?is)<article[^>]*>(.*?)</article>")
    url_pattern = re.compile(r'(?is)<a[^>]+href="([^"]+)"[^>]*class="job-title"[^>]*>(.*?)</a>')
    institution_pattern = re.compile(r'(?is)<a[^>]+class="job-institution"[^>]*>(.*?)</a>')
    posted_pattern = re.compile(r'(?is)<strong[^>]+class="date-posted-value"[^>]*>(.*?)</strong>')
    summary_pattern = re.compile(r'(?is)<p[^>]+class="job-short-description"[^>]*>(.*?)</p>')

    for page in range(1, MAX_PAGES + 1):
        page_url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
        try:
            html = _fetch_text(page_url)
        except Exception:
            continue

        for article in article_pattern.findall(html):
            url_match = url_pattern.search(article)
            if not url_match:
                continue
            url = url_match.group(1).strip()
            title = _clean_text(url_match.group(2))
            if not title:
                continue
            institution_match = institution_pattern.search(article)
            posted_match = posted_pattern.search(article)
            summary_match = summary_pattern.search(article)
            institution = _clean_text(institution_match.group(1) if institution_match else "")
            posted_text = _clean_text(posted_match.group(1) if posted_match else "")
            summary = _clean_text(summary_match.group(1) if summary_match else "")
            key = f"{title.lower()}::{institution.lower()}::{url}"
            if key in seen:
                continue
            seen.add(key)
            combined = f"{title} {summary}"
            results.append(
                {
                    "title": title,
                    "institution": institution or "Unknown Institution",
                    "department": None,
                    "location": "Canada",
                    "country": "CA",
                    "rank": _rank_from_text(combined),
                    "field_tags": _field_tags(query, combined),
                    "employment_type": None,
                    "posted_date": _posted_to_iso(posted_text),
                    "deadline": None,
                    "visa_info": None,
                    "salary_range": None,
                    "requirements": [],
                    "materials": [],
                    "url": url,
                    "source": "academicwork",
                    "source_type": "official-board",
                    "language": "en",
                }
            )

    return results
