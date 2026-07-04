# Universal News Digest

Config-driven collector + renderer for recurring news digests on **any topic**.

The core idea: to create a new digest, add one YAML topic file with sources, search queries, ranking keywords and sections. The same collector/digest pipeline can then run from cron, Hermes, GitHub Actions, or any scheduler.

## Why

A digest should not be hardcoded to AI, finance, health, geopolitics, or any other domain. The implementation is generic:

- topic definition lives in `examples/*.yaml` or your own config file;
- candidates are stored as append-only JSONL;
- sources are grouped and scored by config;
- renderer produces a structured Markdown digest;
- Hermes cron prompts can be generated from the same config.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Quick start

```bash
# Collect from configured RSS/Atom feeds
topic-digest --config examples/ai.yaml --candidates state/ai-candidates.jsonl collect

# Render Markdown digest
topic-digest --config examples/ai.yaml --candidates state/ai-candidates.jsonl render --output out/ai-digest.md

# Generate Hermes cron prompts from the same topic config
topic-digest --config examples/ai.yaml --candidates /home/hermes/.hermes/ai-news-digest/candidates.jsonl hermes-prompts

# Validate a topic config and check live feed health
topic-digest --config examples/geopolitics.yaml validate
topic-digest --config examples/geopolitics.yaml health
```

## Add a new digest topic

Create a YAML file, e.g. `examples/climate.yaml`:

```yaml
topic:
  id: climate
  title: Climate digest
  language: ru
  lookback_hours: 24
  max_items: 10

sources:
  feeds:
    - name: Carbon Brief
      group: news
      url: https://www.carbonbrief.org/feed/
      tags: [climate, policy]
  queries:
    - name: Climate policy
      group: news
      query: climate policy emissions regulation latest
      tags: [policy]

ranking:
  include_keywords: [climate, emissions, energy, policy]
  exclude_keywords: [sponsored, coupon]
  source_weights: {news: 1, official: 2}

sections:
  - id: main
    title: Главное
    tags: [climate, policy]
```

No code changes are required.

## Candidate JSONL schema

```json
{
  "collected_at": "2026-07-04T08:00:00+00:00",
  "source": "OpenAI Blog",
  "source_group": "official",
  "title": "...",
  "url": "https://...",
  "published": "2026-07-04",
  "summary_ru": "Краткая суть на русском.",
  "why_it_matters_ru": "Почему это важно.",
  "tags": ["model", "agents"],
  "importance": 4
}
```

## Hermes integration pattern

Use two cron jobs:

1. **Collector** every 2-4 hours: runs the generated collector prompt, writes JSONL candidates.
2. **Digest** every morning: reads JSONL, verifies important links, ranks/deduplicates, sends Telegram Markdown.

The prompt generator keeps the topic definition in one place:

```bash
topic-digest --config examples/ai.yaml --candidates /home/hermes/.hermes/ai-news-digest/candidates.jsonl hermes-prompts
```

## AI example coverage

`examples/ai.yaml` includes:

- OpenAI, Anthropic, Google DeepMind, Meta, Mistral, xAI, Hugging Face;
- Chinese AI leaders: Qwen/Alibaba, DeepSeek, GLM/Zhipu/Z.ai, Kimi/Moonshot, MiniMax, Baidu ERNIE, Tencent Hunyuan, ByteDance Seed/Doubao;
- arXiv / Hugging Face Papers / Papers with Code style queries;
- engineering blogs and open-source tooling;
- Russian-language sources such as Habr AI.

`examples/geopolitics.yaml` includes:

- agencies/media feeds: Al Jazeera, NPR, BBC, The Guardian;
- analysis/think tanks: War on the Rocks, Foreign Affairs, CSIS, Crisis Group;
- Russian-language context: Meduza plus Carnegie Politika search query;
- query groups for Russia/Ukraine, NATO/Europe, China/Taiwan, Middle East, sanctions/energy/economy, Global South/BRICS, Africa, Arctic and international institutions.

`examples/science-discoveries.yaml` includes:

- science news feeds: ScienceDaily and Phys.org;
- primary/deep-science sources: Nature, Science Magazine and Quanta;
- space coverage from NASA;
- query groups for breakthrough discoveries, physics/materials, space/astronomy, biology/medicine, climate/Earth science and Russian-language science context.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Current limitations

- Built-in collector fetches RSS/Atom feeds. Search queries are intentionally stored in config and used by Hermes prompts or an external search provider.
- Summaries from RSS are extractive. LLM-quality summarization/translation is expected in the Hermes digest job or another summarizer layer.
- No database server is required; JSONL is the storage layer.

## License

MIT
