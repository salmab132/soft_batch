from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Iterable, Optional

import requests


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: str
    published_at: Optional[str] = None  # ISO-8601
    summary: Optional[str] = None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _entry_datetime(entry) -> Optional[datetime]:
    # feedparser may expose several date fields depending on feed
    for attr in ("published", "updated", "created"):
        val = getattr(entry, attr, None)
        if not val:
            continue
        try:
            dt = parsedate_to_datetime(val)
            return dt
        except Exception:
            continue
    return None


def fetch_rss_articles(
    feed_url: str,
    source: str,
    *,
    per_feed_limit: int = 10,
    timeout_s: int = 12,
) -> list[Article]:
    """
    Fetch and parse an RSS/Atom feed into Articles.
    """
    try:
        import feedparser  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "Missing dependency 'feedparser'. Install dependencies with: python -m pip install -r requirements.txt"
        ) from e

    resp = requests.get(
        feed_url,
        timeout=timeout_s,
        headers={"User-Agent": "soft-batch-bot/1.0 (+rss)"},
    )
    resp.raise_for_status()

    parsed = feedparser.parse(resp.content)
    items: list[Article] = []

    for entry in (parsed.entries or [])[:per_feed_limit]:
        url = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not url or not title:
            continue

        dt = _entry_datetime(entry)
        summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
        summary = _strip_html(summary) if summary else None

        items.append(
            Article(
                title=str(title).strip(),
                url=str(url).strip(),
                source=source,
                published_at=_to_iso(dt) if dt else None,
                summary=summary,
            )
        )

    return items


def _dedupe_by_url(articles: Iterable[Article]) -> list[Article]:
    seen: set[str] = set()
    out: list[Article] = []
    for a in articles:
        if a.url in seen:
            continue
        seen.add(a.url)
        out.append(a)
    return out


def get_top_baking_articles(*, limit: int = 5) -> list[Article]:
    """
    Returns the freshest baking-related articles from a small curated set of feeds.
    """
    feeds: list[tuple[str, str]] = [
        ("King Arthur Baking", "https://www.kingarthurbaking.com/blog/feed"),
        ("Sally's Baking Addiction", "https://sallysbakingaddiction.com/feed/"),
        ("Serious Eats", "https://www.seriouseats.com/rss"),
    ]

    all_articles: list[Article] = []
    for source, url in feeds:
        try:
            all_articles.extend(fetch_rss_articles(url, source, per_feed_limit=max(10, limit)))
        except Exception:
            # Best-effort: skip failing feeds (network issues, rate limits, etc.)
            continue

    all_articles = _dedupe_by_url(all_articles)

    def sort_key(a: Article) -> tuple[int, str]:
        # Newest first; unknown dates go last.
        if not a.published_at:
            return (0, "")
        return (1, a.published_at)

    all_articles.sort(key=sort_key, reverse=True)
    return all_articles[:limit]
