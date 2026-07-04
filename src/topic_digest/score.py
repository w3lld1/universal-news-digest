from __future__ import annotations

import re

from .candidates import Candidate
from .config import DigestConfig


def _haystack(candidate: Candidate) -> str:
    return " ".join([candidate.title, candidate.summary_ru, candidate.why_it_matters_ru, " ".join(candidate.tags)]).lower()


def score_candidate(candidate: Candidate, config: DigestConfig) -> int:
    haystack = _haystack(candidate)
    if any(re.search(re.escape(k.lower()), haystack) for k in config.ranking.exclude_keywords):
        return 0
    score = max(1, min(5, int(candidate.importance or 1)))
    score += int(config.ranking.source_weights.get(candidate.source_group, 0))
    score += sum(1 for k in config.ranking.include_keywords if k.lower() in haystack)
    if candidate.source_group in {"official", "china"}:
        score += 1
    return max(0, min(10, score))


def rank_candidates(candidates: list[Candidate], config: DigestConfig) -> list[Candidate]:
    return sorted(
        [c for c in candidates if score_candidate(c, config) > 0],
        key=lambda c: (score_candidate(c, config), c.published, c.collected_at),
        reverse=True,
    )[: config.max_items]
