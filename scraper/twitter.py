from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Optional

from core.markdown_writer import BookmarkData

try:
    from playwright.async_api import async_playwright, BrowserContext, Page
except ImportError:
    async_playwright = None  # type: ignore[assignment]


class TwitterScraper:
    """Playwright-based scraper for Twitter/X bookmarks page."""

    BOOKMARKS_URL = "https://x.com/i/bookmarks"

    def __init__(self) -> None:
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._browser = None

    async def __aenter__(self) -> "TwitterScraper":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def load_session(self, auth_token: str, ct0: str) -> None:
        """Load X session cookies into the browser context."""
        await self._context.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
        ])

    async def scrape_bookmarks(self) -> list[BookmarkData]:
        """Navigate to bookmarks page and extract all visible bookmarks."""
        await self._page.goto(self.BOOKMARKS_URL, wait_until="networkidle")

        seen_ids: set[str] = set()
        results: list[BookmarkData] = []
        consecutive_empty = 0

        while consecutive_empty < 3:
            tweets = await self._extract_tweets()
            new_found = False
            for tweet in tweets:
                tweet_id = tweet.get("url", "")
                if tweet_id and tweet_id not in seen_ids:
                    seen_ids.add(tweet_id)
                    results.append(BookmarkData(
                        url=tweet["url"],
                        source="twitter",
                        author=tweet.get("author", ""),
                        title=tweet.get("text", "")[:100],
                        description=tweet.get("text", ""),
                        thumbnail_url=tweet.get("thumbnail_url", ""),
                        raw_text=tweet.get("text", ""),
                        saved_at=tweet.get("timestamp") or datetime.utcnow(),
                    ))
                    new_found = True

            if new_found:
                consecutive_empty = 0
            else:
                consecutive_empty += 1

            await self._scroll_down()
            await asyncio.sleep(random.uniform(1.5, 4.0))

        return results

    async def _extract_tweets(self) -> list[dict]:
        return await self._page.evaluate("""() => {
            const articles = document.querySelectorAll('article[data-testid="tweet"]');
            const results = [];
            for (const article of articles) {
                try {
                    const linkEl = article.querySelector('a[href*="/status/"]');
                    const url = linkEl ? 'https://x.com' + linkEl.getAttribute('href') : '';
                    const authorEl = article.querySelector('[data-testid="User-Name"] span');
                    const author = authorEl ? authorEl.textContent.trim() : '';
                    const textEl = article.querySelector('[data-testid="tweetText"]');
                    const text = textEl ? textEl.innerText.trim() : '';
                    const imgEl = article.querySelector('[data-testid="tweetPhoto"] img');
                    const thumbnail_url = imgEl ? imgEl.src : '';
                    const timeEl = article.querySelector('time');
                    const timestamp = timeEl ? timeEl.getAttribute('datetime') : null;
                    results.push({ url, author, text, thumbnail_url, timestamp });
                } catch (e) {}
            }
            return results;
        }""")

    async def _scroll_down(self) -> None:
        await self._page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
