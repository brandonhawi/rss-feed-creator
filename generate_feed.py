#!/usr/bin/env python3
"""Generate a static RSS feed from Hugging Face daily papers API."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from xml.sax.saxutils import escape

HF_API_URL = "https://huggingface.co/api/daily_papers"
FEED_URL = "https://brandonhawi.github.io/rss-feed-creator/hf-daily-papers/feed.xml"
SITE_URL = "https://huggingface.co/papers"
OUTPUT_FILE = Path(__file__).parent / "hf-daily-papers" / "feed.xml"


def fetch_papers() -> list[dict]:
    req = Request(HF_API_URL, headers={"User-Agent": "rss-feed-creator/1.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def rfc822(dt_str: str) -> str:
    """Convert ISO 8601 timestamp to RFC 822 format required by RSS."""
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def build_description(paper: dict) -> str:
    parts = []

    ai_summary = paper.get("paper", {}).get("ai_summary", "")
    summary = paper.get("paper", {}).get("summary", "")

    if ai_summary:
        parts.append(f"<p><strong>Summary:</strong> {escape(ai_summary)}</p>")

    if summary:
        parts.append(f"<p><strong>Abstract:</strong> {escape(summary)}</p>")

    keywords = paper.get("paper", {}).get("ai_keywords", [])
    if keywords:
        kw_str = ", ".join(escape(k) for k in keywords)
        parts.append(f"<p><strong>Keywords:</strong> {kw_str}</p>")

    upvotes = paper.get("paper", {}).get("upvotes", 0)
    if upvotes:
        parts.append(f"<p><strong>Upvotes:</strong> {upvotes}</p>")

    github_repo = paper.get("paper", {}).get("githubRepo", "")
    if github_repo:
        parts.append(f'<p><strong>Code:</strong> <a href="{escape(github_repo)}">{escape(github_repo)}</a></p>')

    project_page = paper.get("paper", {}).get("projectPage", "")
    if project_page:
        parts.append(f'<p><strong>Project:</strong> <a href="{escape(project_page)}">{escape(project_page)}</a></p>')

    authors = paper.get("paper", {}).get("authors", [])
    if authors:
        author_names = ", ".join(escape(a.get("name", "")) for a in authors[:10])
        if len(authors) > 10:
            author_names += f" +{len(authors) - 10} more"
        parts.append(f"<p><strong>Authors:</strong> {author_names}</p>")

    return "".join(parts)


def build_feed(papers: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = []
    for paper in papers:
        p = paper.get("paper", {})
        arxiv_id = p.get("id", "")
        title = escape(p.get("title", "Untitled"))
        link = f"https://huggingface.co/papers/{arxiv_id}"
        guid = f"https://arxiv.org/abs/{arxiv_id}"
        pub_date = rfc822(p.get("publishedAt", datetime.now(timezone.utc).isoformat()))
        description = build_description(paper)

        items.append(f"""    <item>
      <title>{title}</title>
      <link>{escape(link)}</link>
      <guid isPermaLink="true">{escape(guid)}</guid>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[{description}]]></description>
    </item>""")

    items_xml = "\n".join(items)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Hugging Face Daily Papers</title>
    <link>{SITE_URL}</link>
    <description>Daily ML/AI papers curated by the Hugging Face community</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{FEED_URL}" rel="self" type="application/rss+xml"/>
    <image>
      <url>https://huggingface.co/favicon.ico</url>
      <title>Hugging Face Daily Papers</title>
      <link>{SITE_URL}</link>
    </image>
{items_xml}
  </channel>
</rss>
"""


def main():
    try:
        papers = fetch_papers()
    except URLError as e:
        print(f"Error fetching papers: {e}", file=sys.stderr)
        sys.exit(1)

    if not papers:
        print("No papers returned from API", file=sys.stderr)
        sys.exit(1)

    feed = build_feed(papers)
    OUTPUT_FILE.write_text(feed, encoding="utf-8")
    print(f"Generated feed.xml with {len(papers)} papers")


if __name__ == "__main__":
    main()
