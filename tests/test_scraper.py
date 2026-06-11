"""Tests for scraper/twitter.py and scraper/runner.py — all external calls mocked."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from core.markdown_writer import BookmarkData
from scraper.twitter import TwitterScraper


MOCK_TWEETS = [
    {
        "url": "https://x.com/user1/status/111",
        "author": "@user1",
        "text": "First tweet text here",
        "thumbnail_url": "https://img.example.com/1.jpg",
        "timestamp": "2026-06-10T10:00:00.000Z",
    },
    {
        "url": "https://x.com/user2/status/222",
        "author": "@user2",
        "text": "Second tweet with content",
        "thumbnail_url": "",
        "timestamp": "2026-06-09T08:00:00.000Z",
    },
]


def _make_scraper() -> TwitterScraper:
    scraper = TwitterScraper()
    page = AsyncMock()
    page.goto = AsyncMock()
    page.evaluate = AsyncMock(return_value=None)
    scraper._page = page
    context = AsyncMock()
    context.add_cookies = AsyncMock()
    scraper._context = context
    return scraper


class TestTwitterScraper:
    @pytest.mark.asyncio
    async def test_scrape_returns_bookmark_data_objects(self):
        scraper = _make_scraper()
        tweet_batches = [MOCK_TWEETS, [], [], []]

        with patch.object(scraper, "_extract_tweets", side_effect=tweet_batches), \
             patch.object(scraper, "_scroll_down", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.scrape_bookmarks()

        assert len(results) == 2
        assert all(isinstance(r, BookmarkData) for r in results)

    @pytest.mark.asyncio
    async def test_scrape_sets_source_twitter(self):
        scraper = _make_scraper()
        tweet_batches = [MOCK_TWEETS, [], [], []]

        with patch.object(scraper, "_extract_tweets", side_effect=tweet_batches), \
             patch.object(scraper, "_scroll_down", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.scrape_bookmarks()

        assert all(r.source == "twitter" for r in results)

    @pytest.mark.asyncio
    async def test_scrape_deduplicates_same_url(self):
        scraper = _make_scraper()
        # Return same tweets twice — should only yield 2 unique bookmarks
        tweet_batches = [MOCK_TWEETS, MOCK_TWEETS, [], [], []]

        with patch.object(scraper, "_extract_tweets", side_effect=tweet_batches), \
             patch.object(scraper, "_scroll_down", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.scrape_bookmarks()

        urls = [r.url for r in results]
        assert len(urls) == len(set(urls))
        assert len(urls) == 2

    @pytest.mark.asyncio
    async def test_scrape_maps_fields_correctly(self):
        scraper = _make_scraper()
        tweet_batches = [MOCK_TWEETS[:1], [], [], []]

        with patch.object(scraper, "_extract_tweets", side_effect=tweet_batches), \
             patch.object(scraper, "_scroll_down", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.scrape_bookmarks()

        bm = results[0]
        assert bm.url == "https://x.com/user1/status/111"
        assert bm.author == "@user1"
        assert bm.raw_text == "First tweet text here"
        assert bm.thumbnail_url == "https://img.example.com/1.jpg"

    @pytest.mark.asyncio
    async def test_scrape_handles_empty_page(self):
        scraper = _make_scraper()
        tweet_batches = [[], [], []]

        with patch.object(scraper, "_extract_tweets", side_effect=tweet_batches), \
             patch.object(scraper, "_scroll_down", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            results = await scraper.scrape_bookmarks()

        assert results == []

    @pytest.mark.asyncio
    async def test_load_session_sets_cookies(self):
        scraper = _make_scraper()
        await scraper.load_session("mytoken", "myct0")

        scraper._context.add_cookies.assert_called_once()
        cookies = scraper._context.add_cookies.call_args[0][0]
        names = {c["name"]: c["value"] for c in cookies}
        assert names["auth_token"] == "mytoken"
        assert names["ct0"] == "myct0"

    @pytest.mark.asyncio
    async def test_scrape_navigates_to_bookmarks_url(self):
        scraper = _make_scraper()
        tweet_batches = [[], [], []]

        with patch.object(scraper, "_extract_tweets", side_effect=tweet_batches), \
             patch.object(scraper, "_scroll_down", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            await scraper.scrape_bookmarks()

        scraper._page.goto.assert_called_once_with(
            TwitterScraper.BOOKMARKS_URL, wait_until="networkidle"
        )

    @pytest.mark.asyncio
    async def test_scrape_stops_after_three_empty_scrolls(self):
        """Scrolling should stop when no new tweets appear 3 times in a row."""
        scraper = _make_scraper()
        call_count = 0

        async def count_extracts():
            nonlocal call_count
            call_count += 1
            return []

        with patch.object(scraper, "_extract_tweets", side_effect=count_extracts), \
             patch.object(scraper, "_scroll_down", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            await scraper.scrape_bookmarks()

        assert call_count == 3


class TestRunnerSync:
    def test_run_twitter_sync_logs_output(self, tmp_path, capsys):
        async def fake_sync(vault_path):
            return 3, 1

        with patch("scraper.runner._sync_twitter", side_effect=fake_sync):
            from scraper.runner import run_twitter_sync
            run_twitter_sync(str(tmp_path / "vault"))

        captured = capsys.readouterr()
        assert "[twitter]" in captured.out
        assert "synced 3 new, 1 skipped" in captured.out

    def test_run_twitter_sync_uses_vault_path_arg(self, tmp_path, capsys):
        vault = str(tmp_path / "myvault")

        async def fake_sync(vault_path):
            assert vault_path == vault
            return 0, 0

        with patch("scraper.runner._sync_twitter", side_effect=fake_sync):
            from scraper.runner import run_twitter_sync
            run_twitter_sync(vault)
