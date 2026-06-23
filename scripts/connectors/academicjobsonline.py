from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://academicjobsonline.org/ajo"
MORE_POSTINGS_URL = f"{BASE_URL}?joblst-------40-d"
CS_CATEGORY_URL = f"{BASE_URL}/cs?"


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
    if "tenure-track" in t or "tenure track" in t or "tenured or tenure-track" in t:
        return "professor-lecture"
    if "teaching-stream" in t or "teaching stream" in t or "teaching track" in t:
        return "professor-lecture"
    if "faculty position" in t or "faculty positions" in t:
        return "professor-lecture"
    if "faculty opening" in t or "faculty openings" in t:
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
    title_l = title.lower()
    # Keep broad aliases to improve filtering in upstream matcher.
    if re.search(r"\b(cs|computer science|informatics|software|computing)\b", title_l):
        tags.append("computer-science")
    if "machine learning" in title_l or re.search(r"\bml\b", title_l):
        tags.append("machine-learning")
    if re.search(r"\bai\b", title_l) or "artificial intelligence" in title_l:
        tags.append("ai")
    if "data science" in title_l:
        tags.append("data-science")
        tags.append("computer-science")
    if "cybersecurity" in title_l or "cyber security" in title_l or "computer security" in title_l:
        tags.append("cybersecurity")
        tags.append("computer-science")
    if "systems" in title_l and "engineering" not in title_l:
        tags.append("computer-science")
    if "physics" in title_l:
        tags.append("physics")
    if "chemistry" in title_l:
        tags.append("chemistry")
    return sorted(set(tags)) or ["academic"]


def _matches_requested_field(query: dict[str, Any], tags: list[str]) -> bool:
    field = (query.get("field") or "").lower()
    if "computer-science" not in field:
        return True
    return "computer-science" in tags


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse public listings from AcademicJobsOnline."""
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None]] = set()

    def add_record(title: str, institution: str, deadline: str | None, url: str) -> None:
        key = (institution.lower(), title.lower(), deadline)
        if key in seen:
            return
        field_tags = _field_tags(query, f"{title} {institution}")
        if not _matches_requested_field(query, field_tags):
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
                "field_tags": field_tags,
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

    def add_records_from_institution_item(item: str) -> None:
        institution_match = re.search(r"(?is)<b>(.*?)</b>", item)
        institution = _clean_text(institution_match.group(1) if institution_match else "Unknown Institution")
        posting_pattern = re.compile(
            r'(?is)\[<a[^>]+href="(?P<jobhref>[^"]+)"[^>]*id="k(?P<id>\d+)"[^>]*>.*?</a>\]\s*'
            r'<span[^>]+id="j\d+"[^>]*>(?P<title>.*?)</span>'
            r'(?P<tail>.*?)(?=\[<a[^>]+href="[^"]+"[^>]*id="k\d+"|</li>|$)'
        )
        for posting in posting_pattern.finditer(item):
            title = _clean_text(posting.group("title"))
            if not title:
                continue
            tail = posting.group("tail")
            deadline_match = re.search(r"(?i)deadline\s*</span>\s*(\d{4}/\d{2}/\d{2})", tail)
            if not deadline_match:
                deadline_match = re.search(r"(?i)deadline\s*(\d{4}/\d{2}/\d{2})", tail)
            deadline = _deadline_to_iso(deadline_match.group(1) if deadline_match else None)
            apply_match = re.search(r'(?is)<a[^>]+href="([^"]*(?:apply-|/apply)[^"]*)"', tail)
            if apply_match:
                url = _abs_url(unescape(apply_match.group(1)))
            else:
                url = _abs_url(unescape(posting.group("jobhref")))
            add_record(title=title, institution=institution, deadline=deadline, url=url)

    def add_records_from_category_block(block: str) -> None:
        heading_match = re.search(r'(?is)<h3[^>]*class="[^"]*\bx1\b[^"]*"[^>]*>(.*?)</h3>', block)
        heading = heading_match.group(1) if heading_match else ""
        heading_links = re.findall(r"(?is)<a[^>]*>(.*?)</a>", heading)
        institution = _clean_text(heading_links[0] if heading_links else heading)
        department = _clean_text(heading_links[1] if len(heading_links) > 1 else "")

        for item in re.findall(r"(?is)<li[^>]*>(.*?)</li>", block):
            posting_match = re.search(
                r'(?is)<a[^>]+href="(?P<jobhref>/ajo/jobs/\d+)"[^>]*id="k(?P<id>\d+)"[^>]*>.*?</a>\]\s*'
                r'<span[^>]+id="j\d+"[^>]*>(?P<title>.*?)</span>(?P<tail>.*)',
                item,
            )
            if not posting_match:
                continue
            title = _clean_text(posting_match.group("title"))
            if not title:
                continue
            tail = posting_match.group("tail")
            deadline_match = re.search(r"(?i)deadline\s*(\d{4}/\d{2}/\d{2})", tail)
            deadline = _deadline_to_iso(deadline_match.group(1) if deadline_match else None)
            apply_match = re.search(r'(?is)<a[^>]+href="([^"]+)"[^>]*>\s*Apply\b', tail)
            if apply_match:
                url = _abs_url(unescape(apply_match.group(1)))
            else:
                url = _abs_url(unescape(posting_match.group("jobhref")))
            display_institution = institution
            if department:
                display_institution = f"{institution}, {department}" if institution else department
            add_record(title=title, institution=display_institution, deadline=deadline, url=url)

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
            add_records_from_institution_item(item)

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

    # Parse the Computer Science category page. This exposes many CS postings that are
    # absent from the homepage deadline block and the stale full-list URL.
    try:
        cs_html = _fetch_text(CS_CATEGORY_URL)
    except Exception:
        cs_html = ""

    if cs_html:
        category_blocks = re.findall(
            r'(?is)<div[^>]+class="[^"]*\bclr\b[^"]*"[^>]*>.*?<ol[^>]+class="[^"]*\bldt\b[^"]*"[^>]*>.*?</ol>\s*</div>',
            cs_html,
        )
        for block in category_blocks:
            add_records_from_category_block(block)

    return results
