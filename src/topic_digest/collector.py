from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen

from .candidates import Candidate
from .config import DigestConfig, FeedSource
from .rss import parse_rss_items
from .score import score_candidate
from .validate import validate_url

MAX_RESPONSE_BYTES = 2_000_000


@dataclass
class SourceError:
    source: str
    url: str
    error: str


@dataclass
class CollectResult:
    candidates: list[Candidate] = field(default_factory=list)
    errors: list[SourceError] = field(default_factory=list)

    @property
    def failed_feeds(self) -> int:
        return len(self.errors)

    @property
    def ok(self) -> bool:
        return bool(self.candidates) or not self.errors


def fetch_url(url: str, timeout: int = 20, max_bytes: int = MAX_RESPONSE_BYTES) -> str:
    problems = validate_url(url)
    if problems:
        raise ValueError("; ".join(problems))
    req = Request(url, headers={"User-Agent": "universal-news-digest/0.1"})
    with urlopen(req, timeout=timeout) as response:  # nosec: validated user-configured http(s) URL
        content_type = response.headers.get_content_type()
        if content_type not in {"application/rss+xml", "application/atom+xml", "application/xml", "text/xml"}:
            # Some feeds are served as text/html; let parse stage decide, but surface the type in health.
            pass
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"response exceeds {max_bytes} bytes")
        return data.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def _is_recent(published: str, lookback_hours: int) -> bool:
    if not published or published == "unknown":
        return True
    try:
        published_date = datetime.fromisoformat(published[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
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


def collect_with_diagnostics(config: DigestConfig) -> CollectResult:
    result = CollectResult()
    for feed in config.feeds:
        try:
            result.candidates.extend(collect_feed(feed, config))
        except Exception as exc:
            result.errors.append(SourceError(source=feed.name, url=feed.url, error=f"{type(exc).__name__}: {exc}"))
    return result


def collect_all_feeds(config: DigestConfig) -> list[Candidate]:
    return collect_with_diagnostics(config).candidates
