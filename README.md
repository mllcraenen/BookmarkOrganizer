# BookmarkOrganizer

Aggregates saved tweets, Instagram posts, and Chrome bookmarks into a single searchable Obsidian vault, served as a static website via Quartz.

## What it does

- Scrapes your Twitter/X bookmarks periodically using Playwright (session-based, no paid API)
- Accepts forwarded links via a Telegram bot (catch-all for anything saved on mobile)
- Converts each bookmark into a structured Markdown note in an Obsidian vault
- Serves the vault as a browsable, graph-linked website via Quartz at `bookmarks.marijncraenen.nl`

## Architecture

```
[Twitter/X scraper]  ──┐
[Telegram bot]        ──┼──► [Markdown writer] ──► [Obsidian vault] ──► [Quartz] ──► website
[Instagram (future)]  ──┘
```

### Components

| Component | Path | Purpose |
|---|---|---|
| `scraper/twitter.py` | Playwright scraper | Pulls Twitter bookmarks every 6h |
| `bot/telegram_bot.py` | python-telegram-bot | Ingests forwarded URLs |
| `core/markdown_writer.py` | Shared writer | Converts bookmark data → `.md` |
| `core/metadata.py` | OG tag fetcher | Enriches bookmarks with title/desc/thumbnail |
| `vault/` | Obsidian vault | The actual notes |
| `quartz/` | Quartz submodule | Static site generator |

### Note format

Each bookmark becomes a Markdown file:

```markdown
---
url: https://x.com/user/status/123
source: twitter
author: "@username"
saved: 2026-06-11
tags: [design, typography]
title: "Great thread on type spacing"
thumbnail: https://...
---

![thumbnail](https://...)

> OG description or tweet text preview

[Open original](https://x.com/user/status/123)
```

## Stack

- Python 3.11+
- Playwright (scraping)
- python-telegram-bot (Telegram ingestion)
- Quartz v4 (static site, served by Caddy)
- Docker Compose (runs on VPS alongside other services)

## Deployment

Runs on `marijncraenen.nl` VPS. Caddy serves the Quartz output at `bookmarks.marijncraenen.nl`.

See `PLAN.md` for full implementation plan and task breakdown.

## Quartz static site

The vault is published as a static site via [Quartz](https://github.com/jackyzha0/quartz) (submodule at `quartz/`).

### Build

```bash
./build.sh
# Output: quartz/public/
```

### Caddy config

Add this block to `/etc/caddy/Caddyfile` on the VPS:

```
bookmarks.marijncraenen.nl {
    root * /home/admin/projects/BookmarkOrganizer/quartz/public
    file_server
}
```

Then reload: `sudo systemctl reload caddy`

### Auto-rebuild on vault change

```bash
# Rebuild whenever a .md file changes in the vault
sudo apt-get install -y inotify-tools
while inotifywait -r -e modify,create,delete vault/; do ./build.sh; done
```

Or add a cron job: `*/15 * * * * cd /home/admin/projects/BookmarkOrganizer && ./build.sh`
