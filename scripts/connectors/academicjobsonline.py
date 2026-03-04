from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://academicjobsonline.org/ajo"
MORE_POSTINGS_URL = f"{BASE_URL}?joblist-------40-d"


def _fetch_text(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; academic-job-search-mcp/0.1)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(req, timeout=15) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def _strip_html(html: str) -> list[str]:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?i)</(p|div|li|h1|h2|h3|h4|h5|br|tr|td)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return [unescape(ln).strip() for ln in text.splitlines() if ln.strip()]


def _abs_url(href: str | None) -> str:
    return urljoin(BASE_URL, href or "")


def _clean_text(html_fragment: str | None) -> str:
    if not html_fragment:
        return ""
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", html_fragment))).strip()


def _rank_from_title(title: str) -> str | None:
    t = title.lower()
    if "postdoc" in t or "postdoctoral" in t:
        return "postdoc-researcher"
    if "research scientist" in t or "researcher" in t:
        return "postdoc-researcher"
    if ("assistant" in t and "professor" in t) or "asst professor" in t:
        return "professor-lecture"
    if ("associate" in t and "professor" in t) or "assoc professor" in t:
        return "professor-lecture"
    if "professor" in t:
        return "professor-lecture"
    if "lecturer" in t:
        return "professor-lecture"
    return None


def _deadline_to_iso(deadline_ymd: str | None) -> str | None:
    if not deadline_ymd:
        return None
    try:
        return datetime.strptime(deadline_ymd, "%Y/%m/%d").date().isoformat()
    except ValueError:
        return None


def _field_tags(query: dict[str, Any], title: str) -> list[str]:
    tags: list[str] = []
    field = (query.get("field") or "").strip()
    if field:
        tags.extend([x for x in field.split("/") if x])
    title_l = title.lower()
    # Keep broad aliases to improve filtering in upstream matcher.
    if re.search(r"\b(cs|computer science|informatics|software)\b", title_l):
        tags.append("computer-science")
    if "machine learning" in title_l or re.search(r"\bml\b", title_l):
        tags.append("machine-learning")
    if re.search(r"\bai\b", title_l) or "artificial intelligence" in title_l:
        tags.append("ai")
    if "physics" in title_l:
        tags.append("physics")
    if "chemistry" in title_l:
        tags.append("chemistry")
    return sorted(set(tags)) or ["academic"]


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse public listings from AcademicJobsOnline."""
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None]] = set()

    def add_record(title: str, institution: str, deadline: str | None, url: str) -> None:
        key = (institution.lower(), title.lower(), deadline)
        if key in seen:
            return
        seen.add(key)
        results.append(
            {
                "title": title,
                "institution": institution or "Unknown Institution",
                "department": None,
                "location": None,
                "country": None,
                "rank": _rank_from_title(title),
                "field_tags": _field_tags(query, title),
                "employment_type": None,
                "posted_date": None,
                "deadline": deadline,
                "visa_info": None,
                "salary_range": None,
                "requirements": [],
                "materials": [],
                "url": url,
                "source": "academicjobsonline",
                "source_type": "official-board",
                "language": "en",
            }
        )

    # Parse homepage "Upcoming Deadlines" block.
    try:
        html = _fetch_text(BASE_URL)
    except Exception:
        html = ""

    if html:
        section_match = re.search(r"(?is)<h2[^>]*>.*?Upcoming Deadlines.*?</h2>\s*<ul[^>]*>(.*?)</ul>", html)
        section = section_match.group(1) if section_match else ""
        items = re.findall(r"(?is)<li[^>]*>(.*?)</li>", section)
        for item in items:
            institution_match = re.search(r"(?is)<b>(.*?)</b>", item)
            institution = _clean_text(institution_match.group(1) if institution_match else "Unknown Institution")
            title_match = re.search(r'(?is)<span[^>]+id="j\d+"[^>]*>(.*?)</span>', item)
            title = _clean_text(title_match.group(1) if title_match else item)
            if not title:
                continue
            deadline_match = re.search(r"(?i)deadline\s*</span>\s*(\d{4}/\d{2}/\d{2})", item)
            deadline = _deadline_to_iso(deadline_match.group(1) if deadline_match else None)
            href_match = re.search(r'(?is)<a[^>]+href="([^"]*(?:apply-|joblist)[^"]*)"', item)
            url = _abs_url(unescape(href_match.group(1))) if href_match else BASE_URL
            add_record(title=title, institution=institution, deadline=deadline, url=url)

    # Parse the full list page behind "more postings...".
    try:
        list_html = _fetch_text(MORE_POSTINGS_URL)
    except Exception:
        list_html = ""

    if list_html:
        # The listing page uses compact repeated "[<a id=kNNN>CODE</a>] <span id=jNNN>TITLE</span> ..."
        # blocks with deadline/apply metadata in the trailing HTML.
        listing_pattern = re.compile(
            r'(?is)\[<a[^>]+id="k(?P<id>\d+)"[^>]*>.*?</a>\]\s*'
            r'<span[^>]+id="j\d+"[^>]*>(?P<title>.*?)</span>(?P<tail>.*?)(?=\[<a[^>]+id="k\d+"|</ol>|<hr)'
        )
        for match in listing_pattern.finditer(list_html):
            title = _clean_text(match.group("title"))
            if not title:
                continue
            tail = match.group("tail")
            deadline_match = re.search(r"(?i)deadline\s*(\d{4}/\d{2}/\d{2})", tail)
            deadline = _deadline_to_iso(deadline_match.group(1) if deadline_match else None)
            apply_match = re.search(r'(?is)<a[^>]+href="([^"]+/jobs/\d+/apply[^"]*)"', tail)
            if apply_match:
                url = _abs_url(unescape(apply_match.group(1)))
            else:
                url = _abs_url(f"/ajo/jobs/{match.group('id')}")
            add_record(title=title, institution="Unknown Institution", deadline=deadline, url=url)

    return results
