# BookmarkOrganizer — Implementation Plan

## Progress tracking

Workers: after completing a task, update `PROGRESS.md` with what was done, then read this file and `PROGRESS.md` to decide the next task. Keep going until all tasks in the current phase are done or you hit a blocker that requires Sir's input.

---

## Phase 1 — Project scaffold & vault setup

### 1.1 Repo structure
- Create directory layout: `scraper/`, `bot/`, `core/`, `vault/`, `docker/`
- Add `pyproject.toml` (Python 3.11, dependencies: playwright, python-telegram-bot, httpx, beautifulsoup4, pydantic)
- Add `.gitignore` (exclude `vault/` content except `.obsidian/` config, exclude session cookies, `.env`)
- Add `docker-compose.yml` with services: `scraper`, `telegram-bot`

### 1.2 Obsidian vault skeleton
- Create `vault/` directory with `.obsidian/` config
- Configure `.obsidian/app.json` with sensible defaults (no spellcheck, readable line length on)
- Create `vault/README.md` as the vault home note
- Add tag index notes: `vault/tags/` — one note per top-level tag (will be auto-linked)

### 1.3 Environment config
- Create `.env.example` with: `TELEGRAM_BOT_TOKEN`, `X_SESSION_COOKIE`, `X_AUTH_TOKEN`, `VAULT_PATH`
- Document in README how to obtain X session cookies (browser devtools → Application → Cookies)

---

## Phase 2 — Core markdown writer

### 2.1 `core/metadata.py`
- `fetch_metadata(url: str) -> dict`: fetches OG tags (title, description, image, site_name) via httpx
- Falls back gracefully if URL is unreachable or has no OG tags
- Returns: `{title, description, thumbnail_url, site_name}`

### 2.2 `core/markdown_writer.py`
- `BookmarkData` pydantic model: `url, source, author, saved_at, tags, title, description, thumbnail_url, raw_text`
- `write_bookmark(data: BookmarkData, vault_path: str) -> Path`
  - Slugifies title for filename (e.g. `great-thread-on-type-spacing.md`)
  - Handles filename collisions by appending date
  - Writes YAML frontmatter + body as specified in README note format
  - Skips write if URL already exists in vault (deduplication — scan frontmatter)
- `find_existing(url: str, vault_path: str) -> Optional[Path]`: checks if a bookmark with that URL already exists

---

## Phase 3 — Twitter/X scraper

### 3.1 `scraper/twitter.py`
- Uses Playwright (async, chromium)
- `TwitterScraper` class:
  - `load_session(cookie_str: str)`: loads X session cookies into browser context
  - `scrape_bookmarks() -> list[BookmarkData]`: navigates to `https://x.com/i/bookmarks`, scrolls to load all visible bookmarks, extracts per-tweet: URL, author handle, tweet text, timestamp, media (first image if present)
  - Adds randomized delays between scrolls (1.5–4s) to mimic human browsing
  - Stops scrolling when no new tweets appear (end of list or duplicates)
  - Returns list of `BookmarkData` objects with `source="twitter"`

### 3.2 `scraper/runner.py`
- `run_twitter_sync()`: calls scraper, passes results to `markdown_writer`, logs count of new/skipped
- Designed to be called by cron or Docker healthcheck
- Logs to stdout in format: `[ISO timestamp] [twitter] synced N new, M skipped`

### 3.3 Scheduling
- Add cron entry in `docker-compose.yml` or a simple `scheduler.py` using `schedule` library
- Default interval: every 6 hours, with ±30 min jitter

---

## Phase 4 — Telegram bot

### 4.1 `bot/telegram_bot.py`
- `python-telegram-bot` (async)
- Listens for messages from Sir's Telegram user ID only (whitelist in `.env`: `ALLOWED_TELEGRAM_USER_ID`)
- Handles:
  - Plain URL message → fetch OG metadata, write bookmark with `source="telegram"`
  - Forwarded tweet link (from Twitter share) → same as above, detect source from URL pattern
  - `/tag <tags>` command: applies tags to the last-added bookmark
  - `/status` command: replies with count of bookmarks per source
- On successful save: replies with the note title and tags applied
- On duplicate: replies "Already saved: <existing note title>"

### 4.2 Tag inference
- Simple heuristic: check URL domain to infer a base tag (e.g. `github.com` → `#dev`, `youtube.com` → `#video`, `x.com` → `#twitter`)
- User can override with `/tag` command after the fact

---

## Phase 5 — Quartz static site

### 5.1 Setup
- Add Quartz v4 as a git submodule at `quartz/`
- Configure `quartz/quartz.config.ts`:
  - `baseUrl: "bookmarks.marijncraenen.nl"`
  - Enable: graph view, backlinks, tags, full-text search
  - Page title: "Bookmarks"
- Point Quartz content source at `../vault/`

### 5.2 Build & serve
- Add `build.sh`: runs `cd quartz && npx quartz build` → outputs to `quartz/public/`
- Caddy config: add `bookmarks.marijncraenen.nl` block pointing to `quartz/public/`
- Add a file-watcher or cron that rebuilds Quartz whenever the vault changes (use `inotifywait` or a post-write hook in the markdown writer)

### 5.3 Caddy entry
```
bookmarks.marijncraenen.nl {
    root * /home/admin/projects/BookmarkOrganizer/quartz/public
    file_server
}
```

---

## Phase 6 — Docker & deployment

### 6.1 `docker/Dockerfile`
- Python 3.11 slim + Playwright chromium install
- Copies `scraper/`, `bot/`, `core/`, installs deps
- Two services in compose: `scraper` (runs scheduler), `telegram-bot` (long-poll)

### 6.2 Deploy to VPS
- Clone repo to `/home/admin/projects/BookmarkOrganizer/`
- Copy `.env` with real values (Sir provides session cookies and bot token)
- `docker compose up -d`
- Add Caddy entry, reload Caddy
- Run initial Twitter sync manually to verify

---

## Phase 7 — Instagram (future, not in scope yet)

Deferred. Options to evaluate when the time comes:
- Playwright scraping of instagram.com/saved (higher ban risk)
- Manual share-to-Telegram fallback (zero risk, slightly more friction)

---

## Decisions log

| Decision | Rationale |
|---|---|
| Playwright over API | X API bookmarks endpoint requires $100/mo Basic tier |
| Quartz over Obsidian Publish | Free, self-hosted, same feature set |
| Markdown vault over database | Obsidian-native, portable, no query layer needed |
| Telegram bot as catch-all | Works from mobile, zero platform risk |
| Session cookies not stored in repo | Security — documented in .env.example only |

---

## Blockers requiring Sir's input

- **X session cookies**: Sir needs to extract these from browser devtools and provide via `.env`
- **Telegram bot token**: Sir needs to create a bot via @BotFather and provide token
- **Telegram user ID**: Sir's Telegram user ID for the whitelist (can be fetched via @userinfobot)
