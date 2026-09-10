"""Generate a static RSS feed from Hugging Face daily papers API."""
from email.utils import format_datetime
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from huggingface_hub import HfApi
from huggingface_hub.hf_api import PaperInfo
import xml.etree.ElementTree as ET

FEED_URL = "https://brandonhawi.github.io/rss-feed-creator/hf-daily-papers/feed.xml"
SITE_URL = "https://huggingface.co/papers"
OUTPUT_FILE = Path(__file__).parent / "hf-daily-papers" / "feed.xml"
ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", ATOM)

def paragraph_tag(label: str, text: str | None) -> str:
    return f'<p><strong>{label}:</strong> {escape(text)}</p>' if text else ""

def build_description(paper: PaperInfo) -> str:
    ai_summary = paper.ai_summary
    summary = paper.summary

    return f"""{paragraph_tag("AI Summary", ai_summary)}
    {paragraph_tag("Abstract", summary)}"""


def build_feed(papers: list[PaperInfo]) -> bytes:
    rss = ET.Element("rss", version="2.0")
    ch = ET.SubElement(rss, "channel")
    ET.SubElement(ch, "title").text = "Hugging Face Daily Papers"
    ET.SubElement(ch, "link").text = SITE_URL
    ET.SubElement(ch, "description").text = "Daily ML/AI papers curated by the Hugging Face community"
    ET.SubElement(ch, "language").text = "en-us"
    ET.SubElement(ch, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc))
    ET.SubElement(ch, f"{{{ATOM}}}link", href=FEED_URL, rel="self", type="application/rss+xml")

    image = ET.SubElement(ch, "image")
    ET.SubElement(image, "url").text = "https://huggingface.co/favicon.ico"
    ET.SubElement(image, "title").text = "Hugging Face Daily Papers"
    ET.SubElement(image, "link").text = SITE_URL

    for paper in papers:
        item = ET.SubElement(ch, "item")
        ET.SubElement(item, "title").text = paper.title
        ET.SubElement(item, "link").text = f"https://huggingface.co/papers/{paper.id}"
        ET.SubElement(item, "guid", isPermaLink="true").text = f"https://arxiv.org/abs/{paper.id}"
        ET.SubElement(item, "pubDate").text = format_datetime(paper.published_at)
        ET.SubElement(item, "description").text = build_description(paper)

    ET.indent(rss, space="  ")
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)


def generate_feed():
    try:
        papers = HfApi().list_daily_papers()
    except Exception as e:
        print(f"Error fetching papers: {e}", file=sys.stderr)
        sys.exit(1)

    feed = build_feed(papers)
    OUTPUT_FILE.write_bytes(feed)
    print(f"Generated feed.xml with {len(papers)} papers")
