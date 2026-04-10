"""
rank.py – Score and rank news articles by importance.

Scoring factors:
  1. Source weight           (from config)
  2. Category weight         (AI/Science ranked higher)
  3. Source type weight      (news > forum > video > blog > paper)
  4. Title keyword boost     (breakthrough, discovery, etc.)
  5. Freshness               (newer articles score higher)

Returns the top-N articles sorted by score descending.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

# How much each factor contributes to the final score (0-100 scale, must sum to 1.0)
WEIGHT_SOURCE = 0.30
WEIGHT_CATEGORY = 0.15
WEIGHT_SOURCE_TYPE = 0.20
WEIGHT_KEYWORD = 0.20
WEIGHT_FRESHNESS = 0.15

# Category importance weights (relative, 1-10)
CATEGORY_WEIGHTS: dict[str, float] = {
    "AI": 10,
    "Robotics": 9,
    "Space": 9,
    "Science": 9,
    "Physics": 8,
    "Biology": 8,
    "Medicine": 9,
    "Chemistry": 7,
    "Psychology": 7,
    "Social Sciences": 6,
    "InfoEng": 7,
    "Technology": 7,
    "Papers": 5,
    "General": 5,
}

# Source type weights: news-first ordering
# news(portal/magazine/institution) > forum(Reddit) > video(YouTube) > blog > paper(arXiv)
SOURCE_TYPE_WEIGHTS: dict[str, float] = {
    "news": 10,
    "forum": 8,
    "video": 7,
    "blog": 6,
    "paper": 5,
}

# Keywords that signal high-importance news
HIGH_IMPORTANCE_KEYWORDS: list[str] = [
    # Science breakthroughs
    "breakthrough", "discovery", "first ever", "first time", "milestone",
    "Nobel", "landmark", "revolutionary", "record-breaking", "unprecedented",
    # AI
    "GPT", "LLM", "large language model", "AGI", "superintelligence",
    "multimodal", "foundation model", "alignment", "RLHF",
    "state-of-the-art", "SOTA", "benchmark",
    # Science/medical
    "cure", "vaccine", "clinical trial", "FDA approval", "gene therapy",
    "quantum", "fusion", "superconductor", "dark matter", "black hole",
    "exoplanet", "Mars", "Moon landing", "space telescope",
    # General significance
    "major", "significant", "critical", "urgent", "world-first",
    "billion", "trillion", "pandemic", "outbreak",
]

# Compiled regex for fast matching
_KW_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in HIGH_IMPORTANCE_KEYWORDS),
    re.IGNORECASE,
)


def _keyword_score(article: dict) -> float:
    """Return 0-10 based on keyword hits in title + summary."""
    text = article.get("title", "") + " " + article.get("summary_raw", "")
    matches = _KW_PATTERN.findall(text)
    # Each unique keyword match adds 2 points; cap at 10
    unique_hits = len(set(m.lower() for m in matches))
    return min(unique_hits * 2.0, 10.0)


def _freshness_score(published_dt: Any, now: datetime) -> float:
    """Return 0-10; higher for more recent articles (decay over 36h)."""
    if published_dt is None:
        return 3.0
    if published_dt.tzinfo is None:
        published_dt = published_dt.replace(tzinfo=timezone.utc)
    age_hours = (now - published_dt).total_seconds() / 3600
    if age_hours < 0:
        age_hours = 0
    # Linear decay: 10 at 0h → 0 at 36h
    return max(0.0, 10.0 * (1.0 - age_hours / 36.0))


def score_article(article: dict, now: datetime) -> float:
    """Compute a composite importance score (0-100)."""
    source_raw = article.get("source_weight", 5)
    source_norm = source_raw  # already 1-10

    category = article.get("category", "General")
    cat_norm = CATEGORY_WEIGHTS.get(category, 5)

    source_type = article.get("source_type", "news")
    type_norm = SOURCE_TYPE_WEIGHTS.get(source_type, 7)

    kw_norm = _keyword_score(article)
    fresh_norm = _freshness_score(article.get("published_dt"), now)

    score = (
        WEIGHT_SOURCE * source_norm * 10
        + WEIGHT_CATEGORY * cat_norm * 10
        + WEIGHT_SOURCE_TYPE * type_norm * 10
        + WEIGHT_KEYWORD * kw_norm * 10
        + WEIGHT_FRESHNESS * fresh_norm * 10
    )
    return round(score, 2)


def rank(articles: list[dict], top_n: int = 30) -> list[dict]:
    """
    Score each article, sort by score descending, return top_n.
    Also attaches 'score' and 'rank' fields to each article.
    """
    now = datetime.now(tz=timezone.utc)
    for art in articles:
        art["score"] = score_article(art, now)

    sorted_articles = sorted(articles, key=lambda a: a["score"], reverse=True)

    top = sorted_articles[:top_n]
    for i, art in enumerate(top, start=1):
        art["rank"] = i

    log.info(
        "Ranked %d articles; top score=%.1f, bottom score=%.1f",
        len(top),
        top[0]["score"] if top else 0,
        top[-1]["score"] if top else 0,
    )
    return top


if __name__ == "__main__":
    import json
    from fetch_news import fetch_all

    articles = fetch_all()
    ranked = rank(articles)
    for a in ranked:
        print(f"[{a['rank']:2d}] {a['score']:.1f}  [{a['category']}] {a['title'][:80]}")
