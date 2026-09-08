#!/usr/bin/env python3

import re
import sys
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


class UpstreamGitHub:
    releases_feed_url = "https://github.com/langchain-ai/langchain/releases.atom"
    releases_page_url = "https://github.com/langchain-ai/langchain/releases"
    user_agent = "rss-feed-creator/1.0"
    timeout_seconds = 30


class BasePackage:
    name = "langchain"
    release_title = re.compile(rf"^{re.escape(name)}==")


class PublishedFeed:
    url = "https://brandonhawi.github.io/rss-feed-creator/langchain-releases/feed.xml"
    file = Path(__file__).parent / "langchain-releases" / "feed.xml"
    title = "LangChain Releases"
    subtitle = (
        f"Releases of the {BasePackage.name} package from langchain-ai/langchain, "
        "filtered from the GitHub releases feed"
    )
    language = "en-US"
    maximum_entries = 100


class XmlNamespace:
    atom = "http://www.w3.org/2005/Atom"
    media_rss = "http://search.yahoo.com/mrss/"
    xml = "http://www.w3.org/XML/1998/namespace"


ElementTree.register_namespace("", XmlNamespace.atom)
ElementTree.register_namespace("media", XmlNamespace.media_rss)


def atom_element(name: str) -> str:
    return f"{{{XmlNamespace.atom}}}{name}"


def xml_attribute(name: str) -> str:
    return f"{{{XmlNamespace.xml}}}{name}"


def download_upstream_releases_feed() -> bytes:
    request = Request(UpstreamGitHub.releases_feed_url, headers={"User-Agent": UpstreamGitHub.user_agent})
    with urlopen(request, timeout=UpstreamGitHub.timeout_seconds) as response:
        return response.read()


def entries_in(feed_xml: bytes) -> list[ElementTree.Element]:
    return ElementTree.fromstring(feed_xml).findall(atom_element("entry"))


def text_of(entry: ElementTree.Element, element_name: str) -> str:
    element = entry.find(atom_element(element_name))
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def is_release_of_base_package(entry: ElementTree.Element) -> bool:
    return BasePackage.release_title.match(text_of(entry, "title")) is not None


def entries_already_published() -> list[ElementTree.Element]:
    if not PublishedFeed.file.exists():
        return []
    try:
        return entries_in(PublishedFeed.file.read_bytes())
    except ElementTree.ParseError as parse_error:
        print(f"Warning: could not parse the published feed, starting fresh: {parse_error}", file=sys.stderr)
        return []


def merged_newest_first(
    published_entries: list[ElementTree.Element],
    upstream_entries: list[ElementTree.Element],
) -> list[ElementTree.Element]:
    entries_by_id: dict[str, ElementTree.Element] = {}
    for entry in published_entries + upstream_entries:
        entry_id = text_of(entry, "id")
        if entry_id:
            entries_by_id[entry_id] = entry
    newest_first = sorted(entries_by_id.values(), key=lambda entry: text_of(entry, "updated"), reverse=True)
    return newest_first[: PublishedFeed.maximum_entries]


def current_utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_feed_containing(entries: list[ElementTree.Element]) -> str:
    feed = ElementTree.Element(atom_element("feed"), {xml_attribute("lang"): PublishedFeed.language})
    ElementTree.SubElement(feed, atom_element("id")).text = PublishedFeed.url
    ElementTree.SubElement(feed, atom_element("title")).text = PublishedFeed.title
    ElementTree.SubElement(feed, atom_element("subtitle")).text = PublishedFeed.subtitle
    ElementTree.SubElement(
        feed, atom_element("link"), {"rel": "alternate", "type": "text/html", "href": UpstreamGitHub.releases_page_url}
    )
    ElementTree.SubElement(
        feed, atom_element("link"), {"rel": "self", "type": "application/atom+xml", "href": PublishedFeed.url}
    )
    ElementTree.SubElement(feed, atom_element("updated")).text = (
        text_of(entries[0], "updated") if entries else current_utc_timestamp()
    )
    feed.extend(entries)
    ElementTree.indent(feed, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(feed, encoding="unicode") + "\n"


def exit_with_error(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    try:
        upstream_feed = download_upstream_releases_feed()
    except URLError as download_error:
        exit_with_error(f"Error fetching releases feed: {download_error}")

    try:
        upstream_entries = entries_in(upstream_feed)
    except ElementTree.ParseError as parse_error:
        exit_with_error(f"Error parsing releases feed: {parse_error}")

    if not upstream_entries:
        exit_with_error("No entries returned from releases feed")

    base_package_releases = [entry for entry in upstream_entries if is_release_of_base_package(entry)]
    feed_entries = merged_newest_first(entries_already_published(), base_package_releases)

    PublishedFeed.file.parent.mkdir(parents=True, exist_ok=True)
    PublishedFeed.file.write_text(render_feed_containing(feed_entries), encoding="utf-8")
    print(
        f"Generated feed.xml: {len(base_package_releases)} of {len(upstream_entries)} upstream releases "
        f"matched '{BasePackage.name}==', {len(feed_entries)} entries total"
    )


if __name__ == "__main__":
    main()
