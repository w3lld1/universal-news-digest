from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from topic_digest.candidates import Candidate, CandidateStore, canonical_url
from topic_digest.collector import collect_with_diagnostics
from topic_digest.config import DigestConfig
from topic_digest.render import render_markdown_digest
from topic_digest.rss import parse_rss_items
from topic_digest.score import score_candidate
from topic_digest.validate import validate_config


class TopicDigestTests(unittest.TestCase):
    def test_config_loads_generic_topic_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ai.yaml"
            path.write_text(
                """
topic:
  id: ai
  title: AI digest
  language: ru
  lookback_hours: 24
sources:
  feeds:
    - name: OpenAI
      group: official
      url: https://openai.com/blog/rss.xml
  queries:
    - name: Qwen releases
      group: china
      query: site:qwenlm.github.io Qwen model release
ranking:
  include_keywords: [model, release, qwen]
  exclude_keywords: [coupon]
sections:
  - id: main
    title: Главное
    tags: [model, release]
""".strip(),
                encoding="utf-8",
            )
            cfg = DigestConfig.from_file(path)
        self.assertEqual(cfg.topic_id, "ai")
        self.assertEqual(cfg.title, "AI digest")
        self.assertEqual(cfg.feeds[0].name, "OpenAI")
        self.assertEqual(cfg.queries[0].query, "site:qwenlm.github.io Qwen model release")
        self.assertEqual(cfg.sections[0].title, "Главное")

    def test_candidate_store_deduplicates_by_canonical_url_and_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CandidateStore(Path(tmp) / "candidates.jsonl")
            first = Candidate(
                source="OpenAI",
                source_group="official",
                title="New Model Released",
                url="https://example.com/post?utm_source=x",
                summary_ru="Коротко",
                why_it_matters_ru="Важно",
                tags=["model"],
                importance=4,
            )
            duplicate = Candidate(
                source="Mirror",
                source_group="news",
                title="New Model Released",
                url="https://example.com/post?utm_campaign=y",
                summary_ru="Дубль",
                why_it_matters_ru="Дубль",
                tags=["model"],
                importance=3,
            )
            self.assertEqual(store.append_many([first, duplicate]), 1)
            loaded = store.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(canonical_url(loaded[0].url), "https://example.com/post")

    def test_rss_parser_extracts_items(self) -> None:
        xml = """<?xml version='1.0'?>
<rss><channel><item><title>Release</title><link>https://x.test/a</link><pubDate>Sat, 04 Jul 2026 08:00:00 GMT</pubDate><description>Body</description></item></channel></rss>
"""
        items = parse_rss_items(xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Release")
        self.assertEqual(items[0].url, "https://x.test/a")

    def test_scoring_uses_topic_keywords_and_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "topic.yaml"
            path.write_text(
                """
topic: {id: test, title: Test, language: ru, lookback_hours: 24}
ranking:
  include_keywords: [model, qwen, agents, UN]
  exclude_keywords: [coupon]
  source_weights: {official: 2, china: 2}
sections: []
sources: {feeds: [], queries: []}
""".strip(),
                encoding="utf-8",
            )
            cfg = DigestConfig.from_file(path)
        good = Candidate(source="Qwen", source_group="china", title="Qwen model release", url="https://q.test")
        bad = Candidate(source="Ad", source_group="news", title="AI coupon deal", url="https://ad.test")
        self.assertGreater(score_candidate(good, cfg), score_candidate(bad, cfg))
        self.assertEqual(score_candidate(bad, cfg), 0)
        substring_false_positive = Candidate(source="BBC", source_group="news", title="Wedding day unfolded", url="https://x.test/wedding")
        self.assertEqual(score_candidate(substring_false_positive, cfg), 0)

    def test_renderer_groups_candidates_by_sections_and_mentions_china_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ai.yaml"
            path.write_text(
                """
topic: {id: ai, title: AI, language: ru, lookback_hours: 24}
sections:
  - {id: models, title: Модели / продукты, tags: [model]}
  - {id: china, title: Китайский AI-блок, groups: [china]}
sources: {feeds: [], queries: []}
ranking: {include_keywords: [], exclude_keywords: []}
""".strip(),
                encoding="utf-8",
            )
            cfg = DigestConfig.from_file(path)
        md = render_markdown_digest(
            cfg,
            [Candidate(source="OpenAI", source_group="official", title="Model [X](bad)", url="https://x.test", summary_ru="Релиз", why_it_matters_ru="Важно", tags=["model"], importance=5)],
            date="2026-07-04",
        )
        self.assertIn("## AI — 2026-07-04", md)
        self.assertIn("### Модели / продукты", md)
        self.assertIn("Model \\[X\\](bad)", md)
        self.assertIn("Ссылка: [Model \\[X\\](bad) — OpenAI](https://x.test)", md)
        self.assertNotIn("Источник: [OpenAI](https://x.test)", md)
        self.assertIn("крупных обновлений не найдено", md)

    def test_scoring_is_config_only_not_domain_hardcoded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "topic.yaml"
            path.write_text("""
topic: {id: test, title: Test, language: ru, lookback_hours: 24}
sources: {feeds: [], queries: []}
ranking: {include_keywords: [release], exclude_keywords: [], source_weights: {official: 0, china: 0, news: 0}}
sections: []
""".strip(), encoding="utf-8")
            cfg = DigestConfig.from_file(path)
        official = Candidate(source="Official", source_group="official", title="release", url="https://o.test")
        china = Candidate(source="China", source_group="china", title="release", url="https://c.test")
        news = Candidate(source="News", source_group="news", title="release", url="https://n.test")
        self.assertEqual(score_candidate(official, cfg), score_candidate(news, cfg))
        self.assertEqual(score_candidate(china, cfg), score_candidate(news, cfg))

    def test_science_discoveries_example_loads_and_validates(self) -> None:
        path = Path(__file__).resolve().parents[1] / "examples" / "science-discoveries.yaml"
        cfg = DigestConfig.from_file(path)
        result = validate_config(path)
        self.assertTrue(result.ok, "\n".join(result.errors + result.warnings))
        self.assertEqual(cfg.topic_id, "science-discoveries")
        self.assertEqual(cfg.title, "Дайджест научных открытий")
        self.assertGreaterEqual(len(cfg.feeds), 5)
        self.assertGreaterEqual(len(cfg.queries), 5)
        self.assertIn("breakthrough", cfg.ranking.include_keywords)
        self.assertTrue(any(section.id == "space" for section in cfg.sections))

    def test_validate_config_reports_bad_feed_url_and_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            path.write_text("""
topic: {id: bad, title: Bad, language: ru, lookback_hours: 24}
sources:
  feeds:
    - name: Localhost
      group: news
      url: http://127.0.0.1/feed.xml
  queries:
    - name: Empty query
      group: news
      query: ""
ranking: {include_keywords: [], exclude_keywords: []}
sections:
  - {id: main, title: Главное, groups: [unknown_group]}
""".strip(), encoding="utf-8")
            result = validate_config(path)
        self.assertFalse(result.ok)
        joined = "\n".join(result.errors + result.warnings)
        self.assertIn("private or localhost", joined)
        self.assertIn("empty query", joined)
        self.assertIn("unknown_group", joined)

    def test_collector_returns_structured_diagnostics_for_failed_feeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "topic.yaml"
            path.write_text("""
topic: {id: test, title: Test, language: ru, lookback_hours: 24}
sources:
  feeds:
    - name: Bad scheme
      group: news
      url: file:///etc/passwd
ranking: {include_keywords: [], exclude_keywords: []}
sections: []
""".strip(), encoding="utf-8")
            cfg = DigestConfig.from_file(path)
        result = collect_with_diagnostics(cfg)
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.failed_feeds, 1)
        self.assertIn("Bad scheme", result.errors[0].source)


if __name__ == "__main__":
    unittest.main()
