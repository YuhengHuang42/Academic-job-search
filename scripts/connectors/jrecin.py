from __future__ import annotations

import re
from datetime import datetime
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
SEARCH_URL = "https://jrecin.jst.go.jp/seek/SeekJorSearch?fn=1&duration=0"


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


def _clean_text(html_fragment: str | None) -> str:
    if not html_fragment:
        return ""
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?is)<[^>]+>", " ", html_fragment))).strip()


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


def _rank_from_text(text: str) -> str | None:
    for jp_label, canonical in JP_RANK_MAP.items():
        if jp_label in text:
            return canonical
    return _rank_from_title(text)


def _jp_date_to_iso(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%Y年%m月%d日", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _language_from_title(title: str) -> str:
    return "ja" if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", title) else "en"


def _field_tags(query: dict[str, Any], text: str) -> list[str]:
    tags: list[str] = []
    text_l = text.lower()
    if (
        "情報" in text
        or "計算機" in text
        or "ロボティクス" in text
        or "知能" in text
        or "人工知能" in text
        or "computer" in text_l
        or "informatics" in text_l
        or "software" in text_l
        or "ai" in text_l
    ):
        tags.append("computer-science")
    if "機械学習" in text or "machine learning" in text_l:
        tags.append("machine-learning")
    if "サイバー" in text or "セキュリティ" in text or "security" in text_l:
        tags.append("security-privacy")
    if "物理" in text or "physics" in text_l:
        tags.append("physics")
    return sorted(set(tags)) or ["academic"]


def _matches_requested_field(query: dict[str, Any], tags: list[str]) -> bool:
    field = (query.get("field") or "").lower()
    if "computer-science" not in field:
        return True
    return "computer-science" in tags


def search(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse public JREC-IN listings from job detail anchors."""
    try:
        html = _fetch_text(SEARCH_URL)
    except Exception:
        html = _fetch_text(BASE_URL)
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    result_card_pattern = re.compile(
        r'(?is)<div[^>]+class="card_header[^"]*"[^>]*>(?P<card>.*?)(?=<div[^>]+class="card_header[^"]*"|</div>\s*</div>\s*</div>\s*<nav|$)'
    )
    for card_match in result_card_pattern.finditer(html):
        card = card_match.group("card")
        title_match = re.search(
            r'(?is)<h5[^>]+class="[^"]*card_title_min[^"]*"[^>]*>\s*'
            r'<a[^>]+href="(?P<href>/seek/SeekJorDetail\?id=[^"]+)"[^>]*>(?P<title>.*?)</a>',
            card,
        )
        if not title_match:
            continue

        href = unescape(title_match.group("href"))
        title = _clean_text(title_match.group("title"))
        if not title:
            continue

        institution_match = re.search(
            r'(?is)<div[^>]+class="my-1"[^>]*font-weight:\s*bold;?[^>]*>(?P<institution>.*?)</div>',
            card,
        )
        institution = _clean_text(institution_match.group("institution") if institution_match else "")
        field_match = re.search(
            r'(?is)fa-list[^<]*</i>\s*<div[^>]*font-weight:\s*500;?[^>]*>(?P<fields>.*?)</div>',
            card,
        )
        fields_text = _clean_text(field_match.group("fields") if field_match else "")
        rank_match = re.search(
            r'(?is)fa-briefcase[^<]*</i>\s*<div[^>]*font-weight:\s*500;?[^>]*>(?P<rank>.*?)</div>',
            card,
        )
        rank_text = _clean_text(rank_match.group("rank") if rank_match else "")
        posted_match = re.search(r"更新日\s*:\s*(\d{4}年\d{2}月\d{2}日)", card)
        deadline_match = re.search(r"募集終了日\s*:\s*(\d{4}年\d{2}月\d{2}日)", card)

        tags = _field_tags(query, f"{title} {fields_text} {rank_text}")
        if not _matches_requested_field(query, tags):
            continue

        key = (href.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "title": title,
                "institution": institution or "Unknown Institution",
                "department": None,
                "location": "Japan",
                "country": "JP",
                "rank": _rank_from_text(f"{title} {rank_text}"),
                "field_tags": tags,
                "employment_type": rank_text or None,
                "posted_date": _jp_date_to_iso(posted_match.group(1) if posted_match else None),
                "deadline": _jp_date_to_iso(deadline_match.group(1) if deadline_match else None),
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

    if results:
        return results

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
        title = _clean_text(match.group(2))
        institution = _clean_text(match.group(3))
        if not title or exclude_hint.search(title):
            continue
        if not institution or exclude_hint.search(institution) or count_hint.match(institution):
            institution = "Unknown Institution"

        key = (href.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)
        tags = _field_tags(query, title)
        if not _matches_requested_field(query, tags):
            continue

        results.append(
            {
                "title": title,
                "institution": institution,
                "department": None,
                "location": "Japan",
                "country": "JP",
                "rank": _rank_from_title(title),
                "field_tags": tags,
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
        title = _clean_text(text_html)
        if not title or exclude_hint.search(title):
            continue

        # Look around this anchor for institution in nearest <p>..</p> block.
        ctx = html[max(0, match.start() - 600) : min(len(html), match.end() + 600)]
        p_candidates = re.findall(r"(?is)<p[^>]*>(.*?)</p>", ctx)
        institution = "Unknown Institution"
        for p_html in p_candidates:
            p_text = _clean_text(p_html)
            if not p_text:
                continue
            if exclude_hint.search(p_text):
                continue
            if count_hint.match(p_text):
                continue
            institution = p_text
            break

        key = (href.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)
        tags = _field_tags(query, title)
        if not _matches_requested_field(query, tags):
            continue

        results.append(
            {
                "title": title,
                "institution": institution,
                "department": None,
                "location": "Japan",
                "country": "JP",
                "rank": _rank_from_title(title),
                "field_tags": tags,
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
