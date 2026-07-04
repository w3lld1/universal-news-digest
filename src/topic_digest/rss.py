from __future__ import annotations

from dataclasses import dataclass
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime


@dataclass(frozen=True)
class RssItem:
    title: str
    url: str
    published: str = "unknown"
    summary: str = ""


def _text(node: ET.Element, *names: str) -> str:
    for name in names:
        child = node.find(name)
        if child is not None and child.text:
            return html.unescape(child.text.strip())
    return ""


def _published(value: str) -> str:
    if not value:
        return "unknown"
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except Exception:
        return value[:10]


def parse_rss_items(xml_text: str) -> list[RssItem]:
    root = ET.fromstring(xml_text.encode("utf-8"))
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    parsed: list[RssItem] = []
    for item in items:
        title = _text(item, "title", "{http://www.w3.org/2005/Atom}title")
        link = _text(item, "link", "guid", "{http://www.w3.org/2005/Atom}id")
        atom_link = item.find("{http://www.w3.org/2005/Atom}link")
        if atom_link is not None and atom_link.attrib.get("href"):
            link = atom_link.attrib["href"]
        summary = _text(item, "description", "summary", "{http://www.w3.org/2005/Atom}summary")
        summary = re.sub(r"<[^>]+>", "", summary).strip()
        published = _published(_text(item, "pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated"))
        if title and link:
            parsed.append(RssItem(title=title, url=link, published=published, summary=summary))
    return parsed
