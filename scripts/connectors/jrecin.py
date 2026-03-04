from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


JP_RANK_MAP = {
    "教授相当": "professor-lecture",
    "准教授相当": "professor-lecture",
    "講師相当": "professor-lecture",
    "助教相当": "professor-lecture",
    "研究員・ポスドク相当": "postdoc-researcher",
}


BASE_URL = "https://jrecin.jst.go.jp/seek/SeekTop"


def _fetch_text(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; academic-job-search-mcp/0.1)",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
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


def _rank_from_title(title: str) -> str | None:
    for jp_label, canonical in JP_RANK_MAP.items():
        if jp_label in title:
            return canonical
    t = title.lower()
    if "postdoc" in t:
        return "postdoc-researcher"
    if "researcher" in t or "研究員" in title:
        return "postdoc-researcher"
    if "assistant professor" in t or "助教" in title:
        return "professor-lecture"
    if "associate professor" in t or "准教授" in title:
        return "professor-lecture"
    if "professor" in t or "教授" in title:
        return "professor-lecture"
    if "lecturer" in t or "講師" in title:
        return "professor-lecture"
    return None


def _language_from_title(title: str) -> str:
    return "ja" if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", title) else "en"


def _field_tags(query: dict[str, Any], title: str) -> list[str]:
    tags: list[str] = []
    field = (query.get("field") or "").strip()
    if field:
        tags.extend([x for x in field.split("/") if x])
    if "情報" in title or "computer" in title.lower():
        tags.append("computer-science")
    if "物理" in title or "physics" in title.lower():
        tags.append("physics")
    return sorted(set(tags)) or ["academic"]


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse public JREC-IN listings from job detail anchors."""
    html = _fetch_text(BASE_URL)
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    card_pattern = re.compile(
        r'(?is)<div[^>]+class="[^"]*single_catagory_text[^"]*"[^>]*>.*?'
        r'<a[^>]+href="(/seek/SeekJorDetail\?id=[^"]+)"[^>]*>(.*?)</a>.*?'
        r"<p[^>]*>(.*?)</p>.*?</div>"
    )
    anchor_pattern = re.compile(r'(?is)<a[^>]+href="(/seek/SeekJorDetail\?id=[^"]+)"[^>]*>(.*?)</a>')
    exclude_hint = re.compile(r"(インターンシップ情報|一覧へ|求人を探す|詳しい条件で求人を検索する)")
    count_hint = re.compile(r"^\d+\s*件$")

    # Parse structured job cards first for better institution fidelity.
    for match in card_pattern.finditer(html):
        href = unescape(match.group(1))
        title = re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", match.group(2)))).strip()
        institution = re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", match.group(3)))).strip()
        if not title or exclude_hint.search(title):
            continue
        if not institution or exclude_hint.search(institution) or count_hint.match(institution):
            institution = "Unknown Institution"

        key = (institution.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "title": title,
                "institution": institution,
                "department": None,
                "location": "Japan",
                "country": "JP",
                "rank": _rank_from_title(title),
                "field_tags": _field_tags(query, title),
                "employment_type": None,
                "posted_date": None,
                "deadline": None,
                "visa_info": None,
                "salary_range": None,
                "requirements": [],
                "materials": [],
                "url": _abs_url(href),
                "source": "jrecin",
                "source_type": "official-board",
                "language": _language_from_title(title),
            }
        )

        if len(results) >= 120:
            return results

    for match in anchor_pattern.finditer(html):
        href = unescape(match.group(1))
        text_html = match.group(2)
        title = re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", text_html))).strip()
        if not title or exclude_hint.search(title):
            continue

        # Look around this anchor for institution in nearest <p>..</p> block.
        ctx = html[max(0, match.start() - 600) : min(len(html), match.end() + 600)]
        p_candidates = re.findall(r"(?is)<p[^>]*>(.*?)</p>", ctx)
        institution = "Unknown Institution"
        for p_html in p_candidates:
            p_text = re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", p_html))).strip()
            if not p_text:
                continue
            if exclude_hint.search(p_text):
                continue
            if count_hint.match(p_text):
                continue
            institution = p_text
            break

        key = (institution.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "title": title,
                "institution": institution,
                "department": None,
                "location": "Japan",
                "country": "JP",
                "rank": _rank_from_title(title),
                "field_tags": _field_tags(query, title),
                "employment_type": None,
                "posted_date": None,
                "deadline": None,
                "visa_info": None,
                "salary_range": None,
                "requirements": [],
                "materials": [],
                "url": _abs_url(href),
                "source": "jrecin",
                "source_type": "official-board",
                "language": _language_from_title(title),
            }
        )

        if len(results) >= 120:
            break

    return results
