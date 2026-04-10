"""
fetch_news.py – Fetch and deduplicate news from RSS feeds.

Output: list of article dicts with keys:
  title, url, summary_raw, published_dt, source_name, category, source_weight
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser
import pytz
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

BEIJING_TZ = pytz.timezone("Asia/Shanghai")

# Request timeout and user-agent
REQUEST_TIMEOUT = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DailyBriefBot/1.0; "
        "+https://github.com/xiubing567/daily-brief)"
    )
}


def load_sources(config_path: str = "config/sources.yml") -> list[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return [s for s in cfg.get("sources", []) if s.get("enabled", True)]


def _strip_html(text: str) -> str:
    """Remove HTML tags and return plain text."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _canonical_url(url: str) -> str:
    """Normalise URL for deduplication (remove utm params, trailing slashes)."""
    parsed = urlparse(url)
    clean = parsed._replace(fragment="", query="").geturl()
    return clean.rstrip("/")


def _title_hash(title: str) -> str:
    """Short hash of a normalised title for similarity-based dedup (non-cryptographic use)."""
    normalised = " ".join(title.lower().split())
    return hashlib.md5(normalised.encode()).hexdigest()  # noqa: S324 – dedup only, not security


def _parse_date(entry: Any) -> datetime | None:
    """Return a timezone-aware datetime for a feed entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = dateutil_parser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

    return None


def _fetch_feed(source: dict) -> list[dict]:
    """Fetch a single RSS feed and return a list of raw article dicts."""
    articles = []
    url = source["url"]
    name = source["name"]
    category = source.get("category", "General")
    weight = source.get("weight", 5)

    try:
        # feedparser can handle the request itself, but we supply headers
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as exc:
        log.warning("Failed to fetch %s (%s): %s", name, url, exc)
        return articles

    for entry in feed.entries:
        link = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", "") or ""
        if not link or not title:
            continue

        # Extract raw summary/description
        summary_raw = ""
        for attr in ("summary", "description", "content"):
            val = getattr(entry, attr, None)
            if val:
                if isinstance(val, list) and val:
                    val = val[0].get("value", "")
                summary_raw = _strip_html(str(val))
                break

        published_dt = _parse_date(entry)

        articles.append(
            {
                "title": title.strip(),
                "url": link.strip(),
                "canonical_url": _canonical_url(link.strip()),
                "title_hash": _title_hash(title),
                "summary_raw": summary_raw[:2000],  # cap length
                "published_dt": published_dt,
                "source_name": name,
                "category": category,
                "source_weight": weight,
            }
        )

    log.info("Fetched %d entries from %s", len(articles), name)
    return articles


def _is_recent(dt: datetime | None, cutoff: datetime) -> bool:
    """Return True if dt is after cutoff (i.e., within the lookback window)."""
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


def _deduplicate(articles: list[dict]) -> list[dict]:
    """Remove duplicates by canonical URL and similar title hash."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict] = []

    for art in articles:
        curl = art["canonical_url"]
        th = art["title_hash"]
        if curl in seen_urls or th in seen_titles:
            continue
        seen_urls.add(curl)
        seen_titles.add(th)
        unique.append(art)

    return unique


def fetch_all(
    config_path: str = "config/sources.yml",
    lookback_hours: int = 36,
    delay_between_feeds: float = 0.3,
) -> list[dict]:
    """
    Fetch news from all enabled sources, filter to recent items,
    deduplicate, and return a list of article dicts.
    """
    sources = load_sources(config_path)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=lookback_hours)
    log.info(
        "Fetching from %d sources, cutoff=%s UTC", len(sources), cutoff.isoformat()
    )

    all_articles: list[dict] = []
    for source in sources:
        articles = _fetch_feed(source)
        all_articles.extend(articles)
        time.sleep(delay_between_feeds)

    # Filter by recency
    recent = [a for a in all_articles if _is_recent(a["published_dt"], cutoff)]
    log.info("Articles after recency filter: %d / %d", len(recent), len(all_articles))

    # Deduplicate
    unique = _deduplicate(recent)
    log.info("Articles after deduplication: %d", len(unique))

    return unique


if __name__ == "__main__":
    import json

    articles = fetch_all()
    for a in articles[:5]:
        print(json.dumps({k: str(v) for k, v in a.items()}, ensure_ascii=False, indent=2))
