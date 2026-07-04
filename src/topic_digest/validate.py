from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from .config import DigestConfig


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _host_is_private_or_local(host: str) -> bool:
    host = host.strip().lower().rstrip(".")
    if host in {"localhost", "0", "0.0.0.0"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        return False


def validate_url(url: str) -> list[str]:
    problems: list[str] = []
    parsed = urlsplit(str(url).strip())
    if parsed.scheme not in {"http", "https"}:
        problems.append(f"unsupported URL scheme: {url}")
    if not parsed.netloc:
        problems.append(f"missing URL host: {url}")
    if parsed.hostname and _host_is_private_or_local(parsed.hostname):
        problems.append(f"private or localhost URL is not allowed: {url}")
    return problems


def validate_config(path: str | Path) -> ValidationResult:
    result = ValidationResult()
    try:
        cfg = DigestConfig.from_file(path)
    except Exception as exc:
        return ValidationResult(errors=[f"cannot load config: {exc}"])

    groups = {f.group for f in cfg.feeds} | {q.group for q in cfg.queries}
    names: set[str] = set()
    for feed in cfg.feeds:
        if not feed.name.strip():
            result.errors.append("feed has empty name")
        if feed.name in names:
            result.warnings.append(f"duplicate source name: {feed.name}")
        names.add(feed.name)
        if feed.max_items <= 0 or feed.max_items > 200:
            result.errors.append(f"feed {feed.name}: max_items must be in 1..200")
        for problem in validate_url(feed.url):
            result.errors.append(f"feed {feed.name}: {problem}")
    for query in cfg.queries:
        if not query.query.strip():
            result.errors.append(f"query {query.name}: empty query")
        if query.name in names:
            result.warnings.append(f"duplicate source name: {query.name}")
        names.add(query.name)
    for section in cfg.sections:
        for group in section.groups:
            if group not in groups:
                result.warnings.append(f"section {section.id}: unknown group {group}")
    if cfg.lookback_hours <= 0 or cfg.lookback_hours > 24 * 30:
        result.errors.append("topic.lookback_hours must be in 1..720")
    if cfg.max_items <= 0 or cfg.max_items > 100:
        result.errors.append("topic.max_items must be in 1..100")
    return result
