from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timezone

import schedule
import time

from core.markdown_writer import write_bookmark
from scraper.twitter import TwitterScraper

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s [%(name)s] %(message)s", level=logging.INFO)


async def _sync_twitter(vault_path: str) -> tuple[int, int]:
    auth_token = os.environ.get("X_AUTH_TOKEN", "")
    ct0 = os.environ.get("X_SESSION_COOKIE", "")

    async with TwitterScraper() as scraper:
        await scraper.load_session(auth_token, ct0)
        bookmarks = await scraper.scrape_bookmarks()

    new_count = 0
    skipped_count = 0
    for bm in bookmarks:
        from core.markdown_writer import find_existing
        if find_existing(bm.url, vault_path):
            skipped_count += 1
        else:
            write_bookmark(bm, vault_path)
            new_count += 1

    return new_count, skipped_count


def run_twitter_sync(vault_path: str | None = None) -> None:
    """Run a single Twitter bookmark sync cycle."""
    if vault_path is None:
        vault_path = os.environ.get("VAULT_PATH", "./vault")

    new_count, skipped_count = asyncio.run(_sync_twitter(vault_path))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] [twitter] synced {new_count} new, {skipped_count} skipped")


def _jittered_interval_hours(base_hours: int = 6, jitter_minutes: int = 30) -> float:
    jitter = random.uniform(-jitter_minutes, jitter_minutes) / 60
    return base_hours + jitter


def _schedule_loop(vault_path: str) -> None:
    def job() -> None:
        run_twitter_sync(vault_path)
        # Reschedule with fresh jitter
        schedule.clear("twitter")
        interval = _jittered_interval_hours()
        schedule.every(interval).hours.do(job).tag("twitter")

    interval = _jittered_interval_hours()
    schedule.every(interval).hours.do(job).tag("twitter")
    logger.info("Twitter sync scheduled every ~6h (±30m jitter)")
    run_twitter_sync(vault_path)  # immediate first run

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    vault_path = os.environ.get("VAULT_PATH", "./vault")
    _schedule_loop(vault_path)
