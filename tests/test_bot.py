"""Tests for bot/telegram_bot.py — all Telegram API calls mocked."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.telegram_bot import BookmarkBot, _extract_url, _infer_tag


# ─── helpers ────────────────────────────────────────────────────────────────

ALLOWED_ID = 12345
BOT_TOKEN = "fake:token"


def make_bot(vault_path: str) -> BookmarkBot:
    with patch("bot.telegram_bot.Application") as mock_app_cls:
        mock_app = MagicMock()
        mock_app_cls.builder.return_value.token.return_value.build.return_value = mock_app
        bot = BookmarkBot(token=BOT_TOKEN, allowed_user_id=ALLOWED_ID, vault_path=vault_path)
        return bot


def make_update(text: str, user_id: int = ALLOWED_ID, args: list[str] | None = None) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def make_context(args: list[str] | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


# ─── unit: helpers ───────────────────────────────────────────────────────────

class TestHelpers:
    def test_extract_url_plain(self):
        assert _extract_url("check this out https://example.com") == "https://example.com"

    def test_extract_url_trims_trailing_punctuation(self):
        assert _extract_url("see https://example.com.") == "https://example.com"

    def test_extract_url_none_when_no_url(self):
        assert _extract_url("no url here") is None

    def test_infer_tag_github(self):
        assert _infer_tag("https://github.com/user/repo") == "dev"

    def test_infer_tag_youtube(self):
        assert _infer_tag("https://www.youtube.com/watch?v=abc") == "video"

    def test_infer_tag_twitter(self):
        assert _infer_tag("https://x.com/user/status/123") == "twitter"

    def test_infer_tag_unknown(self):
        assert _infer_tag("https://random.example.com") is None


# ─── handle_message ─────────────────────────────────────────────────────────

class TestHandleMessage:
    @pytest.mark.asyncio
    async def test_saves_new_url(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("https://github.com/user/repo")
        ctx = make_context()

        with patch("bot.telegram_bot.fetch_metadata", return_value={
            "title": "Cool Repo", "description": "desc", "thumbnail_url": "", "site_name": "GitHub"
        }), patch("bot.telegram_bot.find_existing", return_value=None), \
             patch("bot.telegram_bot.write_bookmark", return_value=tmp_path / "cool-repo.md") as mock_write:
            await bot._handle_message(update, ctx)

        mock_write.assert_called_once()
        update.message.reply_text.assert_called_once()
        reply = update.message.reply_text.call_args[0][0]
        assert "cool-repo" in reply

    @pytest.mark.asyncio
    async def test_duplicate_url_replies_already_saved(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("https://example.com/page")
        ctx = make_context()
        existing_path = tmp_path / "existing-note.md"
        existing_path.touch()

        with patch("bot.telegram_bot.find_existing", return_value=existing_path):
            await bot._handle_message(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "Already saved" in reply
        assert "existing-note" in reply

    @pytest.mark.asyncio
    async def test_no_url_in_message(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("just some text, no links")
        ctx = make_context()

        await bot._handle_message(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "No URL" in reply

    @pytest.mark.asyncio
    async def test_unauthorized_user_ignored(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("https://example.com", user_id=99999)
        ctx = make_context()

        await bot._handle_message(update, ctx)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_twitter_url_sets_source_twitter(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("https://x.com/user/status/123")
        ctx = make_context()

        captured_bm = {}

        def capture_write(bm, vault_path):
            captured_bm["source"] = bm.source
            return tmp_path / "tweet.md"

        with patch("bot.telegram_bot.fetch_metadata", return_value={
            "title": "Tweet", "description": "", "thumbnail_url": "", "site_name": ""
        }), patch("bot.telegram_bot.find_existing", return_value=None), \
             patch("bot.telegram_bot.write_bookmark", side_effect=capture_write):
            await bot._handle_message(update, ctx)

        assert captured_bm["source"] == "twitter"

    @pytest.mark.asyncio
    async def test_tag_inferred_from_domain(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("https://youtube.com/watch?v=x")
        ctx = make_context()
        captured = {}

        def capture_write(bm, vault_path):
            captured["tags"] = bm.tags
            return tmp_path / "video.md"

        with patch("bot.telegram_bot.fetch_metadata", return_value={
            "title": "Video", "description": "", "thumbnail_url": "", "site_name": ""
        }), patch("bot.telegram_bot.find_existing", return_value=None), \
             patch("bot.telegram_bot.write_bookmark", side_effect=capture_write):
            await bot._handle_message(update, ctx)

        assert "video" in captured["tags"]


# ─── /tag command ────────────────────────────────────────────────────────────

class TestTagCommand:
    @pytest.mark.asyncio
    async def test_tag_adds_tags_to_last_note(self, tmp_path):
        note = tmp_path / "my-note.md"
        note.write_text("---\nurl: https://example.com\nsource: telegram\ntags: []\n---\n\nBody\n")

        bot = make_bot(str(tmp_path))
        bot._last_note_path = note

        update = make_update("/tag dev design")
        ctx = make_context(args=["dev", "design"])

        await bot._cmd_tag(update, ctx)

        content = note.read_text()
        assert "dev" in content
        assert "design" in content

    @pytest.mark.asyncio
    async def test_tag_no_last_note(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("/tag dev")
        ctx = make_context(args=["dev"])

        await bot._cmd_tag(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "No recent bookmark" in reply

    @pytest.mark.asyncio
    async def test_tag_no_args(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("---\nurl: https://x.com\nsource: twitter\n---\n")
        bot = make_bot(str(tmp_path))
        bot._last_note_path = note
        update = make_update("/tag")
        ctx = make_context(args=[])

        await bot._cmd_tag(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "Usage" in reply


# ─── /status command ─────────────────────────────────────────────────────────

class TestStatusCommand:
    @pytest.mark.asyncio
    async def test_status_counts_by_source(self, tmp_path):
        for i, source in enumerate(["twitter", "twitter", "telegram"]):
            note = tmp_path / f"note{i}.md"
            note.write_text(f"---\nurl: https://example.com/{i}\nsource: {source}\n---\n")

        bot = make_bot(str(tmp_path))
        update = make_update("/status")
        ctx = make_context()

        await bot._cmd_status(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "twitter: 2" in reply
        assert "telegram: 1" in reply
        assert "total: 3" in reply

    @pytest.mark.asyncio
    async def test_status_empty_vault(self, tmp_path):
        bot = make_bot(str(tmp_path))
        update = make_update("/status")
        ctx = make_context()

        await bot._cmd_status(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "No bookmarks" in reply
