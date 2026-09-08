#!/usr/bin/env python3
"""Generate a filtered Atom feed of LangChain releases.

GitHub's releases.atom for langchain-ai/langchain mixes every package in the
monorepo (langchain-core, langchain-openai, langchain-anthropic, ...). This
script keeps only releases of the base ``langchain`` package, whose tags look
like ``langchain==1.4.0``.

The upstream feed only carries the 10 most recent releases across all
packages, so each run merges new matching entries into the previously
generated feed to accumulate history over time.
"""

import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

SOURCE_URL = "https://github.com/langchain-ai/langchain/releases.atom"
RELEASES_URL = "https://github.com/langchain-ai/langchain/releases"
FEED_URL = "https://brandonhawi.github.io/rss-feed-creator/langchain-releases/feed.xml"
OUTPUT_FILE = Path(__file__).parent / "langchain-releases" / "feed.xml"

# Only keep releases of this package. Tags are formatted "<package>==<version>".
PACKAGE = "langchain"
TITLE_PATTERN = re.compile(rf"^{re.escape(PACKAGE)}==")

# Keep at most this many entries in the generated feed.
MAX_ENTRIES = 100

ATOM_NS = "http://www.w3.org/2005/Atom"
MEDIA_NS = "http://search.yahoo.com/mrss/"
ET.register_namespace("", ATOM_NS)
ET.register_namespace("media", MEDIA_NS)


def atom(tag: str) -> str:
    return f"{{{ATOM_NS}}}{tag}"


def fetch_source() -> bytes:
    req = Request(SOURCE_URL, headers={"User-Agent": "rss-feed-creator/1.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read()


def parse_entries(xml_bytes: bytes) -> list[ET.Element]:
    root = ET.fromstring(xml_bytes)
    return root.findall(atom("entry"))


def entry_text(entry: ET.Element, tag: str) -> str:
    el = entry.find(atom(tag))
    return (el.text or "").strip() if el is not None else ""


def is_base_package_release(entry: ET.Element) -> bool:
    return bool(TITLE_PATTERN.match(entry_text(entry, "title")))


def load_existing_entries() -> list[ET.Element]:
    if not OUTPUT_FILE.exists():
        return []
    try:
        return parse_entries(OUTPUT_FILE.read_bytes())
    except ET.ParseError as e:
        print(f"Warning: could not parse existing feed, starting fresh: {e}", file=sys.stderr)
        return []


def merge_entries(existing: list[ET.Element], new: list[ET.Element]) -> list[ET.Element]:
    """Merge by entry id; new entries win. Newest first, capped at MAX_ENTRIES."""
    by_id: dict[str, ET.Element] = {}
    for entry in existing + new:
        entry_id = entry_text(entry, "id")
        if entry_id:
            by_id[entry_id] = entry
    merged = sorted(by_id.values(), key=lambda e: entry_text(e, "updated"), reverse=True)
    return merged[:MAX_ENTRIES]


def build_feed(entries: list[ET.Element]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated = entry_text(entries[0], "updated") if entries else now

    feed = ET.Element(atom("feed"), {"{http://www.w3.org/XML/1998/namespace}lang": "en-US"})
    ET.SubElement(feed, atom("id")).text = FEED_URL
    ET.SubElement(feed, atom("title")).text = "LangChain Releases"
    ET.SubElement(feed, atom("subtitle")).text = (
        f"Releases of the {PACKAGE} package from langchain-ai/langchain, "
        "filtered from the GitHub releases feed"
    )
    ET.SubElement(feed, atom("link"), {"rel": "alternate", "type": "text/html", "href": RELEASES_URL})
    ET.SubElement(feed, atom("link"), {"rel": "self", "type": "application/atom+xml", "href": FEED_URL})
    ET.SubElement(feed, atom("updated")).text = updated
    feed.extend(entries)

    ET.indent(feed, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(feed, encoding="unicode") + "\n"


def main():
    try:
        source = fetch_source()
    except URLError as e:
        print(f"Error fetching releases feed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        upstream = parse_entries(source)
    except ET.ParseError as e:
        print(f"Error parsing releases feed: {e}", file=sys.stderr)
        sys.exit(1)

    if not upstream:
        print("No entries returned from releases feed", file=sys.stderr)
        sys.exit(1)

    matching = [e for e in upstream if is_base_package_release(e)]
    entries = merge_entries(load_existing_entries(), matching)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(build_feed(entries), encoding="utf-8")
    print(
        f"Generated feed.xml: {len(matching)} of {len(upstream)} upstream releases matched "
        f"'{PACKAGE}==', {len(entries)} entries total"
    )


if __name__ == "__main__":
    main()
