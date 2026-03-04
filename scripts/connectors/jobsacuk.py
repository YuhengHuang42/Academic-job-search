from __future__ import annotations

import re
from datetime import date, datetime
from html import unescape
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://www.jobs.ac.uk"
SEARCH_URL = f"{BASE_URL}/search/"
MAX_PAGES = 3


def _fetch_text(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; academic-job-search-mcp/0.1)",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        },
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def _clean_text(html_fragment: str | None) -> str:
    if not html_fragment:
        return ""
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", html_fragment))).strip()


def _rank_from_text(text: str) -> str | None:
    t = text.lower()
    if "postdoc" in t or "postdoctoral" in t or "researcher" in t or "research fellow" in t:
        return "postdoc-researcher"
    if "professor" in t or "lecturer" in t or "teaching fellow" in t or "instructor" in t:
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
    if "data science" in t:
        tags.append("data-science")
    return sorted(set(tags)) or ["academic"]


def _month_day_to_iso(value: str | None) -> str | None:
    # jobs.ac.uk cards expose dates like "09 Feb" (no year).
    if not value:
        return None
    txt = value.strip()
    for fmt in ("%d %b", "%d %B"):
        try:
            parsed = datetime.strptime(txt, fmt)
            this_year = date.today().year
            candidate = date(this_year, parsed.month, parsed.day)
            # If far in the future, it likely refers to previous year.
            if (candidate - date.today()).days > 180:
                candidate = date(this_year - 1, parsed.month, parsed.day)
            # If far in the past, it likely refers to next year.
            if (date.today() - candidate).days > 300:
                candidate = date(this_year + 1, parsed.month, parsed.day)
            return candidate.isoformat()
        except ValueError:
            continue
    return None


def _country_from_location(location: str | None) -> str | None:
    if not location:
        return None
    loc = location.lower()
    if any(x in loc for x in ["england", "scotland", "wales", "northern ireland", "uk", "united kingdom"]):
        return "GB"
    return None


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse public listings from jobs.ac.uk search results."""
    keywords = (query.get("search_term") or "").strip() or (query.get("field") or "academic jobs")
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    href_pat = re.compile(r'(?is)<a[^>]+href="(/job/[^"]+)"[^>]*>(.*?)</a>')
    dept_pat = re.compile(r'(?is)<div[^>]+class="j-search-result__department"[^>]*>(.*?)</div>')
    employer_pat = re.compile(r'(?is)<div[^>]+class="j-search-result__employer"[^>]*>\s*<b>(.*?)</b>')
    location_pat = re.compile(r"(?is)<div[^>]*>\s*Location:\s*(.*?)\s*</div>")
    salary_pat = re.compile(r"(?is)<strong>\s*Salary:\s*</strong>\s*(.*?)\s*</div>")
    placed_pat = re.compile(r"(?is)<strong>\s*Date Placed:\s*</strong>\s*([0-9]{1,2}\s+[A-Za-z]{3,})")
    closes_pat = re.compile(
        r'(?is)<span[^>]+class="[^"]*j-search-result__date[^"]*"[^>]*>\s*Closes\s*</span>\s*'
        r'<span[^>]+class="[^"]*j-search-result__date--blue[^"]*"[^>]*>(.*?)</span>'
    )

    for page in range(1, MAX_PAGES + 1):
        params = {"keywords": keywords}
        if page > 1:
            params["page"] = str(page)
        page_url = f"{SEARCH_URL}?{urlencode(params)}"
        try:
            html = _fetch_text(page_url)
        except Exception:
            continue

        chunks = re.split(r'(?is)<div[^>]+class="j-search-result__result[^"]*"[^>]*>', html)[1:]
        if not chunks:
            continue

        found_on_page = 0
        for chunk in chunks:
            href_match = href_pat.search(chunk)
            if not href_match:
                continue
            href = href_match.group(1)
            title = _clean_text(href_match.group(2))
            if not title:
                continue

            department = _clean_text(dept_pat.search(chunk).group(1) if dept_pat.search(chunk) else "")
            institution = _clean_text(employer_pat.search(chunk).group(1) if employer_pat.search(chunk) else "")
            location = _clean_text(location_pat.search(chunk).group(1) if location_pat.search(chunk) else "")
            salary = _clean_text(salary_pat.search(chunk).group(1) if salary_pat.search(chunk) else "")
            posted = _clean_text(placed_pat.search(chunk).group(1) if placed_pat.search(chunk) else "")
            deadline = _clean_text(closes_pat.search(chunk).group(1) if closes_pat.search(chunk) else "")

            url = f"{BASE_URL}{href}"
            key = f"{title.lower()}::{institution.lower()}::{location.lower()}::{url}"
            if key in seen:
                continue
            seen.add(key)
            found_on_page += 1

            combined = f"{title} {department} {institution}"
            results.append(
                {
                    "title": title,
                    "institution": institution or "Unknown Institution",
                    "department": department or None,
                    "location": location or None,
                    "country": _country_from_location(location),
                    "rank": _rank_from_text(combined),
                    "field_tags": _field_tags(query, combined),
                    "employment_type": None,
                    "posted_date": _month_day_to_iso(posted),
                    "deadline": _month_day_to_iso(deadline),
                    "visa_info": None,
                    "salary_range": salary or None,
                    "requirements": [],
                    "materials": [],
                    "url": url,
                    "source": "jobsacuk",
                    "source_type": "official-board",
                    "language": "en",
                }
            )

        if found_on_page == 0:
            break

    return results
