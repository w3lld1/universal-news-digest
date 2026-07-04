from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in _TRACKING_KEYS and not k.startswith(_TRACKING_PREFIXES)]
    )
    path = re.sub(r"/+$", "", parts.path) or parts.path
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def title_key(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower(), flags=re.UNICODE).strip()


@dataclass
class Candidate:
    source: str
    source_group: str
    title: str
    url: str
    published: str = "unknown"
    summary_ru: str = ""
    why_it_matters_ru: str = ""
    tags: list[str] = field(default_factory=list)
    importance: int = 1
    collected_at: str = field(default_factory=utc_now_iso)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Candidate":
        fields = {k: data.get(k) for k in cls.__dataclass_fields__ if k in data}  # type: ignore[attr-defined]
        return cls(**fields)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["url"] = canonical_url(self.url)
        data["importance"] = max(1, min(5, int(self.importance)))
        return data

    @property
    def dedupe_keys(self) -> tuple[str, str]:
        return canonical_url(self.url), title_key(self.title)


class CandidateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[Candidate]:
        if not self.path.exists():
            return []
        out: list[Candidate] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(Candidate.from_dict(json.loads(line)))
        return out

    def append_many(self, candidates: list[Candidate]) -> int:
        existing = self.load()
        seen_urls = {c.dedupe_keys[0] for c in existing}
        seen_titles = {c.dedupe_keys[1] for c in existing}
        new: list[Candidate] = []
        for c in candidates:
            url_key, title = c.dedupe_keys
            if url_key in seen_urls or title in seen_titles:
                continue
            seen_urls.add(url_key)
            seen_titles.add(title)
            new.append(c)
        if not new:
            return 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            for c in new:
                fh.write(json.dumps(c.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return len(new)
