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
CUTOFF_HOURS = 24
MAX_ITEMS = 40
SIMILARITY_THRESHOLD = 0.75

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


def _is_recent(date_str: str) -> bool:
    dt = _parse_date(date_str)
    if dt is None:
        return True  # include items whose date cannot be parsed
    return dt >= datetime.now(tz=timezone.utc) - timedelta(hours=CUTOFF_HOURS)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Strip HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


# ---------------------------------------------------------------------------
# Feed parsers
# ---------------------------------------------------------------------------

def _parse_rss(root: ET.Element, source_url: str) -> list[dict]:
    channel = root.find("channel")
    if channel is None:
        return []
    source = _clean(channel.findtext("title") or source_url)
    items = []
    for item in channel.findall("item"):
        title = _clean(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        pub_date = (
            item.findtext("pubDate")
            or item.findtext(f"{{{_NS_DC}}}date")
            or ""
        )
        if not title or not link or not _is_recent(pub_date):
            continue
        description = _clean(
            item.findtext(f"{{{_NS_CONTENT}}}encoded")
            or item.findtext("description")
            or ""
        )[:600]
        items.append({"title": title, "url": link, "description": description, "source": source})
    return items


def _parse_atom(root: ET.Element, source_url: str) -> list[dict]:
    ns = _NS_ATOM
    source = _clean(root.findtext(f"{{{ns}}}title") or source_url)
    items = []
    for entry in root.findall(f"{{{ns}}}entry"):
        title = _clean(entry.findtext(f"{{{ns}}}title") or "")
        # Prefer rel="alternate", fall back to first link with an href
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
        if not title or not link or not _is_recent(pub_date):
            continue
        description = _clean(
            entry.findtext(f"{{{ns}}}summary")
            or entry.findtext(f"{{{ns}}}content")
            or ""
        )[:600]
        items.append({"title": title, "url": link, "description": description, "source": source})
    return items


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_feed(url: str) -> list[dict]:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "daily-ai-digest/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except requests.RequestException as e:
        print(f"[fetch] HTTP error {url}: {e}", file=sys.stderr)
        return []
    except ET.ParseError as e:
        print(f"[fetch] XML error {url}: {e}", file=sys.stderr)
        return []

    tag = root.tag
    if tag == f"{{{_NS_ATOM}}}feed":
        return _parse_atom(root, url)
    # RSS 2.0 (root tag "rss") or any unrecognised root that has a channel child
    return _parse_rss(root, url)


def fetch_all_feeds() -> list[dict]:
    items = []
    for url in RSS_FEEDS:
        items.extend(_fetch_feed(url))
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
    print("[fetch] Fetching RSS feeds...")
    raw = fetch_all_feeds()
    print(f"[fetch] Raw items: {len(raw)}")

    deduped = deduplicate(raw)
    print(f"[fetch] After deduplication: {len(deduped)}")

    capped = deduped[:MAX_ITEMS]
    print(f"[fetch] Capped at: {len(capped)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(capped, f, indent=2, ensure_ascii=False)
    print(f"[fetch] Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
