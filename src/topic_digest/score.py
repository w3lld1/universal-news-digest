from __future__ import annotations

import re

from .candidates import Candidate
from .config import DigestConfig


def _haystack(candidate: Candidate) -> str:
    return " ".join([candidate.title, candidate.summary_ru, candidate.why_it_matters_ru, " ".join(candidate.tags)]).lower()


def _term_matches(term: str, haystack: str) -> bool:
    term = term.lower().strip()
    if not term:
        return False
    if re.search(r"\w", term):
        return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", haystack))
    return term in haystack


def score_candidate(candidate: Candidate, config: DigestConfig) -> int:
    haystack = _haystack(candidate)
    if any(_term_matches(k, haystack) for k in config.ranking.exclude_keywords):
        return 0
    matched_include = sum(1 for k in config.ranking.include_keywords if _term_matches(k, haystack))
    if config.ranking.include_keywords and matched_include == 0:
        return 0
    score = max(1, min(5, int(candidate.importance or 1)))
    score += int(config.ranking.source_weights.get(candidate.source_group, 0))
    score += matched_include
    return max(0, min(10, score))


def rank_candidates(candidates: list[Candidate], config: DigestConfig) -> list[Candidate]:
    return sorted(
        [c for c in candidates if score_candidate(c, config) > 0],
        key=lambda c: (score_candidate(c, config), c.published, c.collected_at),
        reverse=True,
    )[: config.max_items]
