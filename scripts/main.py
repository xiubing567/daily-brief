"""
main.py – Orchestrates the full daily-brief pipeline:
  1. Fetch news from RSS sources
  2. Rank articles by importance
  3. Translate titles and generate bilingual summaries
  4. Render HTML + Markdown report
  5. Send email to subscribers

Usage:
  python scripts/main.py [--top-n 20] [--lookback-hours 36] \
                         [--config config/sources.yml] \
                         [--subscribers config/subscribers.json] \
                         [--output-dir reports] \
                         [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fetch_news import fetch_all
from rank import rank
from render_report import get_email_subject, render_html, save_reports
from send_email import load_subscribers, send
from translate import translate_and_summarise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the daily-brief pipeline")
    p.add_argument("--top-n", type=int, default=20, help="Number of top articles (default: 20)")
    p.add_argument(
        "--lookback-hours",
        type=int,
        default=36,
        help="How many hours back to include articles (default: 36)",
    )
    p.add_argument("--config", default="config/sources.yml", help="Sources config file")
    p.add_argument(
        "--subscribers",
        default="config/subscribers.json",
        help="Subscribers JSON file",
    )
    p.add_argument("--output-dir", default="reports", help="Directory for report output")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate reports but do NOT send email",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    log.info("═" * 60)
    log.info("daily-brief pipeline starting")
    log.info("  top-n=%d  lookback=%dh  dry-run=%s", args.top_n, args.lookback_hours, args.dry_run)
    log.info("═" * 60)

    # ── Step 1: Fetch ─────────────────────────────────────────────────
    log.info("Step 1/5 – Fetching news from RSS sources…")
    articles = fetch_all(
        config_path=args.config,
        lookback_hours=args.lookback_hours,
    )
    if not articles:
        log.warning("No articles fetched. Exiting.")
        sys.exit(0)

    # ── Step 2: Rank ──────────────────────────────────────────────────
    log.info("Step 2/5 – Ranking %d articles…", len(articles))
    top_articles = rank(articles, top_n=args.top_n)

    # ── Step 3: Translate ─────────────────────────────────────────────
    log.info("Step 3/5 – Translating and summarising %d articles…", len(top_articles))
    top_articles = translate_and_summarise(top_articles)

    # ── Step 4: Render ────────────────────────────────────────────────
    log.info("Step 4/5 – Rendering HTML + Markdown reports…")
    html_path, md_path = save_reports(top_articles, output_dir=args.output_dir)

    # Preview first 3 items in log
    for art in top_articles[:3]:
        log.info(
            "  [#%d] [%s] %s",
            art.get("rank", "?"),
            art.get("category", ""),
            art.get("title_en", art.get("title", ""))[:80],
        )

    # ── Step 5: Send email ────────────────────────────────────────────
    if args.dry_run:
        log.info("Step 5/5 – DRY RUN: skipping email send.")
        log.info("Reports saved: %s, %s", html_path, md_path)
    else:
        log.info("Step 5/5 – Sending email…")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        subject = get_email_subject()
        subscribers = load_subscribers(args.subscribers)
        send(
            html_content=html_content,
            subject=subject,
            subscribers=subscribers,
            subscribers_path=args.subscribers,
        )

    log.info("═" * 60)
    log.info("daily-brief pipeline complete  ✓")
    log.info("═" * 60)


if __name__ == "__main__":
    main()
