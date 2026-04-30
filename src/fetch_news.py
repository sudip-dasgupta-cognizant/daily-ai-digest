import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime

import requests

sys.path.insert(0, os.path.dirname(__file__))
from sources import RSS_FEEDS

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_FILE = os.path.join(REPO_ROOT, "news_items.json")
CUTOFF_HOURS = 48      # primary window
FALLBACK_HOURS = 72    # used if primary window yields 0 items
MAX_ITEMS = 40
SIMILARITY_THRESHOLD = 0.75

# Generic browser UA to avoid bot-blocking on news/blog feeds
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_NS_ATOM = "http://www.w3.org/2005/Atom"
_NS_CONTENT = "http://purl.org/rss/1.0/modules/content/"
_NS_DC = "http://purl.org/dc/elements/1.1/"


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    # RFC 2822 (RSS <pubDate>): "Wed, 30 Apr 2026 09:00:00 +0000"
    try:
        return parsedate_to_datetime(date_str).astimezone(timezone.utc)
    except Exception:
        pass
    # ISO 8601 (Atom <published>/<updated>): "2026-04-30T09:00:00Z"
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        pass
    return None


def _is_recent(date_str: str, cutoff_hours: int) -> bool:
    dt = _parse_date(date_str)
    if dt is None:
        return True  # include items whose date cannot be parsed
    return dt >= datetime.now(tz=timezone.utc) - timedelta(hours=cutoff_hours)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


# ---------------------------------------------------------------------------
# Feed parsers — return (filtered_items, total_count, source_name)
# ---------------------------------------------------------------------------

def _parse_rss(root: ET.Element, source_url: str, cutoff_hours: int) -> tuple[list[dict], int, str]:
    channel = root.find("channel")
    if channel is None:
        return [], 0, source_url
    source = _clean(channel.findtext("title") or source_url)
    total = 0
    items = []
    for item in channel.findall("item"):
        total += 1
        title = _clean(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        pub_date = (
            item.findtext("pubDate")
            or item.findtext(f"{{{_NS_DC}}}date")
            or ""
        )
        if not title or not link or not _is_recent(pub_date, cutoff_hours):
            continue
        description = _clean(
            item.findtext(f"{{{_NS_CONTENT}}}encoded")
            or item.findtext("description")
            or ""
        )[:600]
        items.append({"title": title, "url": link, "description": description, "source": source})
    return items, total, source


def _parse_atom(root: ET.Element, source_url: str, cutoff_hours: int) -> tuple[list[dict], int, str]:
    ns = _NS_ATOM
    source = _clean(root.findtext(f"{{{ns}}}title") or source_url)
    total = 0
    items = []
    for entry in root.findall(f"{{{ns}}}entry"):
        total += 1
        title = _clean(entry.findtext(f"{{{ns}}}title") or "")
        link = ""
        for link_el in entry.findall(f"{{{ns}}}link"):
            href = link_el.get("href", "")
            if not href:
                continue
            if link_el.get("rel", "alternate") == "alternate":
                link = href
                break
            if not link:
                link = href
        pub_date = (
            entry.findtext(f"{{{ns}}}published")
            or entry.findtext(f"{{{ns}}}updated")
            or ""
        )
        if not title or not link or not _is_recent(pub_date, cutoff_hours):
            continue
        description = _clean(
            entry.findtext(f"{{{ns}}}summary")
            or entry.findtext(f"{{{ns}}}content")
            or ""
        )[:600]
        items.append({"title": title, "url": link, "description": description, "source": source})
    return items, total, source


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_feed(url: str, cutoff_hours: int) -> list[dict]:
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except requests.RequestException as e:
        print(f"[fetch]   FAIL  {url}", file=sys.stderr)
        print(f"          {e}", file=sys.stderr)
        return []
    except ET.ParseError as e:
        print(f"[fetch]   FAIL  {url} (XML parse error: {e})", file=sys.stderr)
        return []

    if root.tag == f"{{{_NS_ATOM}}}feed":
        items, total, source = _parse_atom(root, url, cutoff_hours)
    else:
        items, total, source = _parse_rss(root, url, cutoff_hours)

    print(f"[fetch]   OK    {source!r}: {len(items)}/{total} items within {cutoff_hours}h window")
    return items


def fetch_all_feeds(cutoff_hours: int) -> list[dict]:
    items = []
    for url in RSS_FEEDS:
        items.extend(_fetch_feed(url, cutoff_hours))
    return items


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _titles_similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= SIMILARITY_THRESHOLD


def deduplicate(items: list[dict]) -> list[dict]:
    seen: list[str] = []
    unique: list[dict] = []
    for item in items:
        if not any(_titles_similar(item["title"], s) for s in seen):
            seen.append(item["title"])
            unique.append(item)
    return unique


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"[fetch] Fetching {len(RSS_FEEDS)} feeds (primary window: {CUTOFF_HOURS}h)...")
    raw = fetch_all_feeds(CUTOFF_HOURS)

    if not raw:
        print(
            f"[fetch] 0 items with {CUTOFF_HOURS}h window — "
            f"retrying with {FALLBACK_HOURS}h fallback window..."
        )
        raw = fetch_all_feeds(FALLBACK_HOURS)
        if not raw:
            print("[fetch] WARNING: 0 items after fallback. Writing empty digest.", file=sys.stderr)
        else:
            print(f"[fetch] Fallback succeeded: {len(raw)} raw items with {FALLBACK_HOURS}h window")

    print(f"[fetch] Total raw items: {len(raw)}")

    deduped = deduplicate(raw)
    print(f"[fetch] After deduplication: {len(deduped)}")

    capped = deduped[:MAX_ITEMS]
    print(f"[fetch] Capped at: {len(capped)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(capped, f, indent=2, ensure_ascii=False)
    print(f"[fetch] Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
