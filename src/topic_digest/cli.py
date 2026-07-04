from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .candidates import Candidate, CandidateStore
from .collector import collect_all_feeds
from .config import DigestConfig
from .hermes import collector_prompt, digest_prompt
from .render import render_markdown_digest


def _cmd_collect(args: argparse.Namespace) -> int:
    cfg = DigestConfig.from_file(args.config)
    store = CandidateStore(args.candidates)
    found = collect_all_feeds(cfg)
    added = store.append_many(found)
    print(json.dumps({"found": len(found), "added": added, "candidates": str(args.candidates)}, ensure_ascii=False))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    cfg = DigestConfig.from_file(args.config)
    candidates = CandidateStore(args.candidates).load()
    markdown = render_markdown_digest(cfg, candidates, date=args.date or date.today().isoformat())
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    payload = json.loads(args.json)
    candidate = Candidate.from_dict(payload)
    added = CandidateStore(args.candidates).append_many([candidate])
    print(json.dumps({"added": added}, ensure_ascii=False))
    return 0


def _cmd_hermes_prompts(args: argparse.Namespace) -> int:
    cfg = DigestConfig.from_file(args.config)
    print("# Collector prompt\n")
    print(collector_prompt(cfg, args.candidates))
    print("\n# Digest prompt\n")
    print(digest_prompt(cfg, args.candidates))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="topic-digest", description="Config-driven news digest collector/renderer")
    parser.add_argument("--config", required=True, help="Topic YAML config")
    parser.add_argument("--candidates", default="./state/candidates.jsonl", help="JSONL candidate store")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Collect candidates from configured RSS/Atom feeds")
    collect.set_defaults(func=_cmd_collect)

    render = sub.add_parser("render", help="Render markdown digest from candidate store")
    render.add_argument("--output", help="Write markdown to this file instead of stdout")
    render.add_argument("--date", help="Digest date override")
    render.set_defaults(func=_cmd_render)

    add = sub.add_parser("add", help="Append one JSON candidate to the store")
    add.add_argument("json", help="Candidate JSON object")
    add.set_defaults(func=_cmd_add)

    prompts = sub.add_parser("hermes-prompts", help="Generate Hermes cron prompts from topic config")
    prompts.set_defaults(func=_cmd_hermes_prompts)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
