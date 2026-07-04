from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen

from .candidates import Candidate
from .config import DigestConfig, FeedSource
from .rss import parse_rss_items
from .score import score_candidate


def fetch_url(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "universal-news-digest/0.1"})
    with urlopen(req, timeout=timeout) as response:  # nosec: user-configured URLs are expected
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def _is_recent(published: str, lookback_hours: int) -> bool:
    if not published or published == "unknown":
        return True
    try:
        published_date = datetime.fromisoformat(published[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    # Date-only RSS values have no time component; allow the whole day.
    return published_date.date() >= cutoff.date()


def collect_feed(feed: FeedSource, config: DigestConfig) -> list[Candidate]:
    xml = fetch_url(feed.url)
    candidates: list[Candidate] = []
    for item in parse_rss_items(xml):
        if not _is_recent(item.published, config.lookback_hours):
            continue
        c = Candidate(
            source=feed.name,
            source_group=feed.group,
            title=item.title,
            url=item.url,
            published=item.published,
            summary_ru=item.summary[:240],
            why_it_matters_ru="Совпало с тематическими правилами дайджеста; проверь источник для деталей.",
            tags=feed.tags,
            importance=3,
            raw={"feed_url": feed.url},
        )
        if score_candidate(c, config) > 0:
            candidates.append(c)
        if len(candidates) >= feed.max_items:
            break
    return candidates


def collect_all_feeds(config: DigestConfig) -> list[Candidate]:
    out: list[Candidate] = []
    for feed in config.feeds:
        try:
            out.extend(collect_feed(feed, config))
        except Exception as exc:
            out.append(
                Candidate(
                    source=feed.name,
                    source_group="collector_error",
                    title=f"Collector error for {feed.name}",
                    url=feed.url,
                    summary_ru=str(exc),
                    tags=["error"],
                    importance=1,
                )
            )
    return [c for c in out if c.source_group != "collector_error"]
