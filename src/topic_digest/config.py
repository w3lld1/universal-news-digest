from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    group: str = "news"
    tags: list[str] = field(default_factory=list)
    max_items: int = 25


@dataclass(frozen=True)
class QuerySource:
    name: str
    query: str
    group: str = "news"
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    tags: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Ranking:
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    source_weights: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class DigestConfig:
    topic_id: str
    title: str
    language: str
    lookback_hours: int
    feeds: list[FeedSource]
    queries: list[QuerySource]
    ranking: Ranking
    sections: list[Section]
    max_items: int = 10

    @classmethod
    def from_file(cls, path: str | Path) -> "DigestConfig":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        topic = raw.get("topic") or {}
        sources = raw.get("sources") or {}
        ranking = raw.get("ranking") or {}
        return cls(
            topic_id=str(topic.get("id") or Path(path).stem),
            title=str(topic.get("title") or topic.get("id") or Path(path).stem),
            language=str(topic.get("language") or "ru"),
            lookback_hours=int(topic.get("lookback_hours") or 24),
            max_items=int(topic.get("max_items") or raw.get("max_items") or 10),
            feeds=[_feed(x) for x in sources.get("feeds", []) or []],
            queries=[_query(x) for x in sources.get("queries", []) or []],
            ranking=Ranking(
                include_keywords=list(ranking.get("include_keywords", []) or []),
                exclude_keywords=list(ranking.get("exclude_keywords", []) or []),
                source_weights={str(k): int(v) for k, v in (ranking.get("source_weights", {}) or {}).items()},
            ),
            sections=[_section(x) for x in raw.get("sections", []) or []],
        )

    def to_prompt_context(self) -> str:
        groups = sorted({f.group for f in self.feeds} | {q.group for q in self.queries})
        feeds = "\n".join(f"- [{f.group}] {f.name}: {f.url}" for f in self.feeds)
        queries = "\n".join(f"- [{q.group}] {q.name}: {q.query}" for q in self.queries)
        sections = "\n".join(f"- {s.title} (tags={s.tags}, groups={s.groups})" for s in self.sections)
        return (
            f"Topic: {self.title} ({self.topic_id})\n"
            f"Language: {self.language}\nLookback hours: {self.lookback_hours}\nMax items: {self.max_items}\n"
            f"Source groups: {', '.join(groups)}\n\nFeeds:\n{feeds}\n\nSearch queries:\n{queries}\n\nSections:\n{sections}\n"
        )


def _feed(raw: dict[str, Any]) -> FeedSource:
    return FeedSource(
        name=str(raw["name"]),
        url=str(raw["url"]),
        group=str(raw.get("group") or "news"),
        tags=list(raw.get("tags", []) or []),
        max_items=int(raw.get("max_items") or 25),
    )


def _query(raw: dict[str, Any]) -> QuerySource:
    return QuerySource(
        name=str(raw["name"]),
        query=str(raw["query"]),
        group=str(raw.get("group") or "news"),
        tags=list(raw.get("tags", []) or []),
    )


def _section(raw: dict[str, Any]) -> Section:
    return Section(
        id=str(raw["id"]),
        title=str(raw["title"]),
        tags=list(raw.get("tags", []) or []),
        groups=list(raw.get("groups", []) or []),
    )
