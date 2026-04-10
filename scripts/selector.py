"""
select.py – Quota-based article selection strategy.

Instead of a simple global Top-N (which lets one hot category dominate),
this module implements per-category quotas so every important category
gets at least one slot, then fills the remainder with global top-scorers.

Strategy (方案2):
  - Core categories (AI, Technology, Science, Medicine, Space, Robotics):
    take up to CORE_QUOTA (default 2) highest-scored articles each.
  - Other categories (Physics, Chemistry, Biology, Psychology,
    Social Sciences, InfoEng, Papers, General, etc.):
    take up to OTHER_QUOTA (default 1) highest-scored article each.
  - If total < target (default 30), fill with the next highest-scored
    articles from the global remaining pool (any category).
  - If total > target after quotas (rare), truncate by global score.
  - Finally, reassign contiguous global rank numbers ordered by score.
"""

from __future__ import annotations

import logging
from collections import defaultdict

log = logging.getLogger(__name__)

# Categories that get higher per-category quota
CORE_CATEGORIES: frozenset[str] = frozenset(
    {"AI", "Technology", "Science", "Medicine", "Space", "Robotics"}
)

CORE_QUOTA: int = 2    # max articles per core category in the quota pass
OTHER_QUOTA: int = 1   # max articles per other category in the quota pass
DEFAULT_TOTAL: int = 30


def select(
    articles: list[dict],
    total: int = DEFAULT_TOTAL,
    core_quota: int = CORE_QUOTA,
    other_quota: int = OTHER_QUOTA,
) -> list[dict]:
    """
    Apply quota-based selection and return up to *total* articles with
    updated 'rank' fields (1-based, ordered by score descending).

    Articles must already have a 'score' field (set by rank.rank()).
    """
    if not articles:
        return []

    # Sort all articles by score descending so quota picks are the best
    sorted_all = sorted(articles, key=lambda a: a["score"], reverse=True)

    # ── Phase 1: per-category quota ───────────────────────────────────
    selected_ids: set[int] = set()   # track by id() to avoid copies
    quota_picks: list[dict] = []
    cat_counts: dict[str, int] = defaultdict(int)

    for art in sorted_all:
        cat = art.get("category", "General")
        quota = core_quota if cat in CORE_CATEGORIES else other_quota
        if cat_counts[cat] < quota:
            quota_picks.append(art)
            selected_ids.add(id(art))
            cat_counts[cat] += 1

    log.info(
        "Quota phase: selected %d articles across %d categories",
        len(quota_picks),
        len(cat_counts),
    )

    # ── Phase 2: fill remaining slots from global pool ────────────────
    remaining_needed = total - len(quota_picks)
    if remaining_needed > 0:
        for art in sorted_all:
            if remaining_needed <= 0:
                break
            if id(art) not in selected_ids:
                quota_picks.append(art)
                selected_ids.add(id(art))
                remaining_needed -= 1
        log.info(
            "Fill phase: added %d articles to reach target=%d",
            total - len(quota_picks) + remaining_needed,
            total,
        )

    # ── Phase 3: sort final selection by score, assign global ranks ───
    final = sorted(quota_picks, key=lambda a: a["score"], reverse=True)
    final = final[:total]  # safety truncation
    for i, art in enumerate(final, start=1):
        art["rank"] = i

    log.info(
        "select(): returning %d articles (top=%.1f, bottom=%.1f)",
        len(final),
        final[0]["score"] if final else 0,
        final[-1]["score"] if final else 0,
    )
    return final
