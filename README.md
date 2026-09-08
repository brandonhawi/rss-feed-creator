# rss-feed-creator

A tool for creating and managing RSS feeds. Feeds are regenerated daily by GitHub Actions and served via GitHub Pages.

## Feeds

| Feed | URL | Generator |
| --- | --- | --- |
| Hugging Face Daily Papers | https://brandonhawi.github.io/rss-feed-creator/hf-daily-papers/feed.xml | `generate_feed.py` |
| LangChain Releases (`langchain` package only) | https://brandonhawi.github.io/rss-feed-creator/langchain-releases/feed.xml | `generate_langchain_feed.py` |

### LangChain Releases

GitHub's `releases.atom` for `langchain-ai/langchain` includes every package in the monorepo
(`langchain-core`, `langchain-openai`, `langchain-anthropic`, ...). This feed keeps only releases
of the base `langchain` package, i.e. tags matching `langchain==<version>`.

Because the upstream feed only exposes the 10 most recent releases across all packages, each run
merges new matching releases into the previously generated feed so history accumulates over time.
