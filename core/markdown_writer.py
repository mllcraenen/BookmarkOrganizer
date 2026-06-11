from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from slugify import slugify


class BookmarkData(BaseModel):
    url: str
    source: str
    author: str = ""
    saved_at: datetime = None  # type: ignore[assignment]
    tags: list[str] = []
    title: str = ""
    description: str = ""
    thumbnail_url: str = ""
    raw_text: str = ""

    def model_post_init(self, __context: object) -> None:
        if self.saved_at is None:
            object.__setattr__(self, "saved_at", datetime.now(timezone.utc))


def find_existing(url: str, vault_path: str) -> Optional[Path]:
    """Return the path of an existing note whose frontmatter url matches, or None."""
    vault = Path(vault_path)
    for md_file in vault.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            if fm and fm.get("url") == url:
                return md_file
        except OSError:
            continue
    return None


def write_bookmark(data: BookmarkData, vault_path: str) -> Path:
    """Write a bookmark note to the vault. Returns the path written.

    Skips write and returns existing path if URL already present.
    """
    vault = Path(vault_path)
    vault.mkdir(parents=True, exist_ok=True)

    existing = find_existing(data.url, vault_path)
    if existing:
        return existing

    filename = _make_filename(data, vault)
    content = _render_note(data)
    filename.write_text(content, encoding="utf-8")
    return filename


def _make_filename(data: BookmarkData, vault: Path) -> Path:
    raw = data.title or data.url
    slug = slugify(raw, max_length=80) or "bookmark"
    candidate = vault / f"{slug}.md"
    if not candidate.exists():
        return candidate
    date_suffix = data.saved_at.strftime("%Y-%m-%d") if data.saved_at else date.today().isoformat()
    candidate = vault / f"{slug}-{date_suffix}.md"
    if not candidate.exists():
        return candidate
    # Final fallback: append counter
    i = 2
    while True:
        candidate = vault / f"{slug}-{date_suffix}-{i}.md"
        if not candidate.exists():
            return candidate
        i += 1


def _render_note(data: BookmarkData) -> str:
    saved_str = data.saved_at.strftime("%Y-%m-%d") if data.saved_at else date.today().isoformat()
    frontmatter = {
        "url": data.url,
        "source": data.source,
        "saved": saved_str,
    }
    if data.author:
        frontmatter["author"] = data.author
    if data.tags:
        frontmatter["tags"] = data.tags
    if data.title:
        frontmatter["title"] = data.title
    if data.thumbnail_url:
        frontmatter["thumbnail"] = data.thumbnail_url

    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    lines = ["---", fm_str.rstrip(), "---", ""]

    if data.thumbnail_url:
        lines += [f"![thumbnail]({data.thumbnail_url})", ""]

    body = data.description or data.raw_text
    if body:
        lines += [f"> {body}", ""]

    lines += [f"[Open original]({data.url})", ""]
    return "\n".join(lines)


def _parse_frontmatter(text: str) -> Optional[dict]:
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
