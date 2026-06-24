# PROGRESS.md

Workers: read this file + PLAN.md at the start of each task. After completing a task, update this file, then pick the next task and continue. Only stop if you hit a blocker listed at the bottom of this file or at the end of PLAN.md.

---

## Status

**Current phase:** All in-scope tasks complete (Phases 1–5, excluding Phase 6 deployment and Phase 7 Instagram)
**Last updated:** 2026-06-11
**Next task:** None — awaiting Sir's review and PR merge

---

## Completed tasks

- [x] **task-bo-001** — Scaffold: repo structure, pyproject.toml, docker-compose.yml, .env.example, .gitignore, vault/.obsidian config, tag index notes
- [x] **task-bo-002** — core/metadata.py: fetch_metadata() with httpx + OG tag parsing + fallback; 6 tests
- [x] **task-bo-003** — core/markdown_writer.py: BookmarkData pydantic model, write_bookmark(), find_existing() deduplication; 15 tests
- [x] **task-bo-004** — scraper/twitter.py + runner.py: TwitterScraper with Playwright (mocked), randomized delays (1.5–4s), 3-empty-scroll stop condition, run_twitter_sync() orchestrator; 10 tests
- [x] **task-bo-005** — bot/telegram_bot.py: whitelist-gated bot, URL handler, /tag, /status, domain→tag inference; 18 tests
- [x] **task-bo-006** — Quartz v5 submodule, quartz.config.yaml (bookmarks.marijncraenen.nl, graph/search/tags/backlinks), build.sh, Caddy config documented in README

**Total tests: 49 — all passing**

---

## Blockers (stop and report if hit)

- X session cookies not yet provided by Sir — needed for Phase 3 live run
- Telegram bot token not yet provided by Sir — needed for Phase 4 live run
- Sir's Telegram user ID not yet confirmed — needed for bot whitelist (ALLOWED_TELEGRAM_USER_ID in .env)

Workers: for Phases 1–2 and Phase 5, no credentials are needed. Build and test those fully. For Phases 3–4, build the code and write tests with mocked data, but do not attempt a live run.
