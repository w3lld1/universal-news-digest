from __future__ import annotations

from .config import DigestConfig


def collector_prompt(config: DigestConfig, candidates_path: str) -> str:
    return f"""Ты — фоновый коллектор новостей для topic digest.

{config.to_prompt_context()}

Задача: собрать кандидаты за последние ~{config.lookback_hours} часов и сохранить новые строки JSONL в `{candidates_path}`.
Формат JSONL: {{"collected_at":"ISO", "source":"...", "source_group":"...", "title":"...", "url":"...", "published":"YYYY-MM-DD or unknown", "summary_ru":"...", "why_it_matters_ru":"...", "tags":[...], "importance":1-5}}.

Правила: дедуп по URL/title; не выдумывать; выбирать high-signal материалы; писать summary_ru/why_it_matters_ru на русском.
""".strip()


def digest_prompt(config: DigestConfig, candidates_path: str) -> str:
    return f"""Ты — автор утреннего дайджеста на русском.

{config.to_prompt_context()}

Прочитай кандидаты из `{candidates_path}`, при необходимости проверь важные URL, выбери до {config.max_items} пунктов, дедуплицируй и пришли Markdown-дайджест.
Формат: заголовок, секции из config, для каждого пункта прямая ссылка на статью в формате `Ссылка: [название статьи — источник](url)`, 'Что открыть полностью', 'Шум отфильтрован'. Не больше 3500-4500 символов, если день не исключительный.
""".strip()
