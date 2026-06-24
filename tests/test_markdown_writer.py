import re
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from core.markdown_writer import BookmarkData, find_existing, write_bookmark


@pytest.fixture
def vault(tmp_path):
    return str(tmp_path / "vault")


def make_bookmark(**kwargs) -> BookmarkData:
    defaults = {
        "url": "https://example.com/post",
        "source": "telegram",
        "title": "Example Post",
        "saved_at": datetime(2026, 6, 11, 10, 0, 0),
    }
    defaults.update(kwargs)
    return BookmarkData(**defaults)


def _read_fm(path: Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    return yaml.safe_load(m.group(1))


class TestWriteBookmark:
    def test_creates_file(self, vault):
        bm = make_bookmark()
        path = write_bookmark(bm, vault)
        assert path.exists()

    def test_filename_is_slugified_title(self, vault):
        bm = make_bookmark(title="Great Thread on Type Spacing")
        path = write_bookmark(bm, vault)
        assert path.name == "great-thread-on-type-spacing.md"

    def test_frontmatter_contains_url_and_source(self, vault):
        bm = make_bookmark(url="https://x.com/user/status/123", source="twitter")
        path = write_bookmark(bm, vault)
        fm = _read_fm(path)
        assert fm["url"] == "https://x.com/user/status/123"
        assert fm["source"] == "twitter"

    def test_frontmatter_tags(self, vault):
        bm = make_bookmark(tags=["dev", "design"])
        path = write_bookmark(bm, vault)
        fm = _read_fm(path)
        assert fm["tags"] == ["dev", "design"]

    def test_frontmatter_thumbnail(self, vault):
        bm = make_bookmark(thumbnail_url="https://img.example.com/thumb.jpg")
        path = write_bookmark(bm, vault)
        fm = _read_fm(path)
        assert fm["thumbnail"] == "https://img.example.com/thumb.jpg"

    def test_body_contains_description(self, vault):
        bm = make_bookmark(description="A really good post about stuff")
        path = write_bookmark(bm, vault)
        content = path.read_text()
        assert "> A really good post about stuff" in content

    def test_body_contains_open_original_link(self, vault):
        bm = make_bookmark(url="https://example.com/post")
        path = write_bookmark(bm, vault)
        content = path.read_text()
        assert "[Open original](https://example.com/post)" in content

    def test_thumbnail_image_in_body(self, vault):
        bm = make_bookmark(thumbnail_url="https://img.example.com/t.jpg")
        path = write_bookmark(bm, vault)
        content = path.read_text()
        assert "![thumbnail](https://img.example.com/t.jpg)" in content

    def test_deduplication_skips_existing_url(self, vault):
        bm = make_bookmark()
        path1 = write_bookmark(bm, vault)
        path2 = write_bookmark(bm, vault)
        assert path1 == path2
        # Only one file should exist
        files = list(Path(vault).glob("*.md"))
        assert len(files) == 1

    def test_collision_appends_date(self, vault):
        bm1 = make_bookmark(url="https://a.com/1", title="Same Title")
        bm2 = make_bookmark(url="https://b.com/2", title="Same Title")
        path1 = write_bookmark(bm1, vault)
        path2 = write_bookmark(bm2, vault)
        assert path1 != path2
        assert "2026-06-11" in path2.name

    def test_fallback_to_url_slug_when_no_title(self, vault):
        bm = make_bookmark(title="", url="https://example.com/some-page")
        path = write_bookmark(bm, vault)
        assert path.name.endswith(".md")
        assert path.exists()


class TestFindExisting:
    def test_returns_none_for_empty_vault(self, vault):
        Path(vault).mkdir(parents=True)
        assert find_existing("https://example.com", vault) is None

    def test_finds_existing_note(self, vault):
        bm = make_bookmark(url="https://example.com/unique")
        written = write_bookmark(bm, vault)
        found = find_existing("https://example.com/unique", vault)
        assert found == written

    def test_returns_none_for_different_url(self, vault):
        bm = make_bookmark(url="https://example.com/a")
        write_bookmark(bm, vault)
        assert find_existing("https://example.com/b", vault) is None

    def test_handles_malformed_frontmatter(self, vault):
        Path(vault).mkdir(parents=True)
        (Path(vault) / "bad.md").write_text("not frontmatter at all")
        assert find_existing("https://example.com", vault) is None
