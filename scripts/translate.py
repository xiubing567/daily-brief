"""
translate.py – Bilingual translation and summarisation.

Strategy (in order of preference):
  1. If OPENAI_API_KEY env var is set → use OpenAI GPT to generate
     high-quality Chinese translations + bilingual summaries.
  2. Otherwise → use deep-translator (Google Translate) for title
     translation, and a simple extractive approach for summaries.

Each article dict is enriched with:
  title_zh      – Chinese title
  title_en      – English title (unchanged)
  summary_en    – English summary (≤80 words)
  summary_zh    – Chinese summary (≤120 Chinese chars)
"""

from __future__ import annotations

import logging
import os
import re
import time

log = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _truncate_words(text: str, max_words: int = 80) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"


def _simple_summary(text: str, max_words: int = 80) -> str:
    """Extract first two sentences or truncate to max_words."""
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = " ".join(sentences[:2]) if sentences else text
    return _truncate_words(summary, max_words)


# ── Google Translate (free, no key needed) ────────────────────────────────────


def _google_translate_batch(texts: list[str], delay: float = 0.5) -> list[str]:
    """Translate a list of texts from English to Chinese using deep-translator."""
    try:
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source="en", target="zh-CN")
        results = []
        for text in texts:
            if not text.strip():
                results.append("")
                continue
            try:
                # Truncate to 4999 chars – Google Translate API limit per request
                translated = translator.translate(text[:4999])
                results.append(translated or text)
            except Exception as exc:
                log.warning("Translation failed for text '%s...': %s", text[:30], exc)
                results.append(text)
            time.sleep(delay)
        return results
    except ImportError:
        log.warning("deep-translator not installed; skipping translation")
        return texts


# ── OpenAI path ───────────────────────────────────────────────────────────────


def _openai_translate_and_summarise(articles: list[dict]) -> list[dict]:
    """Use OpenAI GPT to translate titles and generate bilingual summaries."""
    import openai

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    for art in articles:
        title_en = art.get("title", "")
        summary_raw = art.get("summary_raw", "")

        prompt = (
            "You are a bilingual science/tech editor. "
            "Given the article title and raw summary below, output JSON with keys:\n"
            "  title_zh   : Chinese translation of the title\n"
            "  summary_en : Concise English summary in ≤80 words\n"
            "  summary_zh : Concise Chinese summary in ≤120 Chinese characters\n\n"
            f"Title (EN): {title_en}\n"
            f"Raw summary: {summary_raw[:1500]}\n\n"
            "Respond with ONLY the JSON object, no markdown fences."
        )

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400,
            )
            import json as _json

            raw = resp.choices[0].message.content.strip()
            # Strip potential markdown fences
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = _json.loads(raw)
            art["title_zh"] = data.get("title_zh", title_en)
            art["summary_en"] = data.get("summary_en", _simple_summary(summary_raw))
            art["summary_zh"] = data.get("summary_zh", art["title_zh"])
        except Exception as exc:
            log.warning("OpenAI request failed for '%s': %s", title_en[:40], exc)
            art["title_zh"] = title_en
            art["summary_en"] = _simple_summary(summary_raw)
            art["summary_zh"] = art["summary_en"]

        time.sleep(0.5)  # rate-limit

    return articles


# ── Fallback: deep-translator path ────────────────────────────────────────────


def _fallback_translate_and_summarise(articles: list[dict]) -> list[dict]:
    """
    Build English summaries via extraction, then batch-translate titles
    and summaries to Chinese.
    """
    # Build English summaries first (no API calls)
    for art in articles:
        art["title_en"] = art.get("title", "")
        art["summary_en"] = _simple_summary(art.get("summary_raw", ""))

    # Collect texts to translate
    titles = [art["title_en"] for art in articles]
    summaries = [art["summary_en"] for art in articles]

    log.info("Translating %d titles…", len(titles))
    titles_zh = _google_translate_batch(titles, delay=0.4)

    log.info("Translating %d summaries…", len(summaries))
    summaries_zh = _google_translate_batch(summaries, delay=0.4)

    for art, t_zh, s_zh in zip(articles, titles_zh, summaries_zh):
        art["title_zh"] = t_zh
        art["summary_zh"] = s_zh

    return articles


# ── Public API ────────────────────────────────────────────────────────────────


def translate_and_summarise(articles: list[dict]) -> list[dict]:
    """
    Enrich each article with title_en, title_zh, summary_en, summary_zh.
    Uses OpenAI if OPENAI_API_KEY is set; otherwise uses deep-translator.
    """
    if not articles:
        return articles

    use_openai = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    if use_openai:
        log.info("Using OpenAI for translation/summarisation (%d articles)…", len(articles))
        articles = _openai_translate_and_summarise(articles)
    else:
        log.info(
            "OPENAI_API_KEY not set; using deep-translator fallback (%d articles)…",
            len(articles),
        )
        articles = _fallback_translate_and_summarise(articles)

    # Ensure all fields exist
    for art in articles:
        art.setdefault("title_en", art.get("title", ""))
        art.setdefault("title_zh", art.get("title_en", ""))
        art.setdefault("summary_en", _simple_summary(art.get("summary_raw", "")))
        art.setdefault("summary_zh", art.get("summary_en", ""))

    return articles
