from __future__ import annotations

from collections import defaultdict
from datetime import date

from .candidates import Candidate
from .config import DigestConfig, Section
from .score import rank_candidates


def _matches(candidate: Candidate, section: Section) -> bool:
    if section.groups and candidate.source_group in section.groups:
        return True
    if section.tags and set(section.tags).intersection(candidate.tags):
        return True
    return not section.groups and not section.tags


def _item(candidate: Candidate, idx: int) -> str:
    summary = candidate.summary_ru or "Краткое описание не заполнено; см. источник."
    why = candidate.why_it_matters_ru or "Может быть полезно для мониторинга темы."
    return (
        f"{idx}. **{candidate.title}**\n"
        f"   - Коротко: {summary}\n"
        f"   - Почему важно: {why}\n"
        f"   - Источник: [{candidate.source}]({candidate.url})\n"
    )


def render_markdown_digest(config: DigestConfig, candidates: list[Candidate], date: str | None = None) -> str:
    today = date or __import__("datetime").date.today().isoformat()
    ranked = rank_candidates(candidates, config)
    used: set[str] = set()
    lines = [f"## {config.title} — {today}\n\n"]
    if not ranked:
        return "".join(lines + ["Значимых новостей по выбранным источникам не найдено.\n"])

    for section in config.sections:
        section_items = [c for c in ranked if c.url not in used and _matches(c, section)]
        lines.append(f"### {section.title}\n\n")
        if not section_items:
            lines.append("- За период крупных обновлений не найдено.\n\n")
            continue
        for idx, candidate in enumerate(section_items, 1):
            used.add(candidate.url)
            lines.append(_item(candidate, idx))
        lines.append("\n")

    leftovers = [c for c in ranked if c.url not in used]
    if leftovers:
        lines.append("### Остальное важное\n\n")
        for idx, candidate in enumerate(leftovers, 1):
            lines.append(_item(candidate, idx))
        lines.append("\n")

    lines.append("### Что открыть полностью\n\n")
    for idx, candidate in enumerate(ranked[:3], 1):
        lines.append(f"{idx}. [{candidate.title}]({candidate.url}) — {candidate.why_it_matters_ru or candidate.summary_ru}\n")
    lines.append("\n### Шум отфильтрован\n\n")
    lines.append("Мелкие повторы, маркетинговые анонсы без фактов и низкосигнальные публикации не включались.\n")
    return "".join(lines)
