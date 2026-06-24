from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from core.markdown_writer import BookmarkData, find_existing, write_bookmark
from core.metadata import fetch_metadata

logger = logging.getLogger(__name__)

_DOMAIN_TAGS: dict[str, str] = {
    "github.com": "dev",
    "gist.github.com": "dev",
    "stackoverflow.com": "dev",
    "youtube.com": "video",
    "youtu.be": "video",
    "x.com": "twitter",
    "twitter.com": "twitter",
}
_URL_RE = re.compile(r"https?://[^\s]+")


def _infer_tag(url: str) -> Optional[str]:
    for domain, tag in _DOMAIN_TAGS.items():
        if domain in url:
            return tag
    return None


def _extract_url(text: str) -> Optional[str]:
    m = _URL_RE.search(text)
    return m.group(0).rstrip(".,)>\"'") if m else None


class BookmarkBot:
    def __init__(self, token: str, allowed_user_id: int, vault_path: str) -> None:
        self.token = token
        self.allowed_user_id = allowed_user_id
        self.vault_path = vault_path
        self._last_note_path: Optional[Path] = None
        self.app = Application.builder().token(token).build()
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.app.add_handler(CommandHandler("tag", self._cmd_tag))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

    def _is_allowed(self, update: Update) -> bool:
        return update.effective_user is not None and update.effective_user.id == self.allowed_user_id

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            return

        text = update.message.text or ""
        url = _extract_url(text)
        if not url:
            await update.message.reply_text("No URL found in message.")
            return

        existing = find_existing(url, self.vault_path)
        if existing:
            await update.message.reply_text(f"Already saved: {existing.stem}")
            return

        meta = fetch_metadata(url)
        tag = _infer_tag(url)
        tags = [tag] if tag else []

        source = "twitter" if ("x.com" in url or "twitter.com" in url) else "telegram"
        bm = BookmarkData(
            url=url,
            source=source,
            title=meta["title"],
            description=meta["description"],
            thumbnail_url=meta["thumbnail_url"],
            tags=tags,
        )
        note_path = write_bookmark(bm, self.vault_path)
        self._last_note_path = note_path

        tag_str = f" [{', '.join(f'#{t}' for t in tags)}]" if tags else ""
        await update.message.reply_text(f"Saved: {note_path.stem}{tag_str}")

    async def _cmd_tag(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            return

        if not self._last_note_path or not self._last_note_path.exists():
            await update.message.reply_text("No recent bookmark to tag.")
            return

        new_tags = [t.lstrip("#") for t in (context.args or []) if t]
        if not new_tags:
            await update.message.reply_text("Usage: /tag <tag1> [tag2 ...]")
            return

        text = self._last_note_path.read_text(encoding="utf-8")
        import yaml, re as _re
        fm_match = _re.match(r"^---\n(.*?)\n---", text, _re.DOTALL)
        if fm_match:
            fm = yaml.safe_load(fm_match.group(1)) or {}
            existing_tags = fm.get("tags") or []
            merged = list(dict.fromkeys(existing_tags + new_tags))
            fm["tags"] = merged
            fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
            new_text = f"---\n{fm_str.rstrip()}\n---" + text[fm_match.end():]
            self._last_note_path.write_text(new_text, encoding="utf-8")

        tag_str = ", ".join(f"#{t}" for t in new_tags)
        await update.message.reply_text(f"Tagged {self._last_note_path.stem} with {tag_str}")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            return

        counts: dict[str, int] = {}
        vault = Path(self.vault_path)
        for md_file in vault.rglob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
                import re as _re, yaml
                m = _re.match(r"^---\n(.*?)\n---", text, _re.DOTALL)
                if m:
                    fm = yaml.safe_load(m.group(1)) or {}
                    source = fm.get("source", "unknown")
                    counts[source] = counts.get(source, 0) + 1
            except OSError:
                continue

        if not counts:
            await update.message.reply_text("No bookmarks saved yet.")
            return

        lines = [f"{source}: {n}" for source, n in sorted(counts.items())]
        lines.append(f"total: {sum(counts.values())}")
        await update.message.reply_text("\n".join(lines))

    def run(self) -> None:
        logger.info("Starting Telegram bot (polling)...")
        self.app.run_polling()


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    user_id = int(os.environ["ALLOWED_TELEGRAM_USER_ID"])
    vault_path = os.environ.get("VAULT_PATH", "./vault")
    bot = BookmarkBot(token=token, allowed_user_id=user_id, vault_path=vault_path)
    bot.run()


if __name__ == "__main__":
    main()
