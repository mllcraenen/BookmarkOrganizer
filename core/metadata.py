from __future__ import annotations

import httpx
from bs4 import BeautifulSoup


_TIMEOUT = httpx.Timeout(10.0)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BookmarkOrganizer/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_metadata(url: str) -> dict:
    """Fetch OG/meta tags from a URL. Returns empty-string values on any failure."""
    result = {"title": "", "description": "", "thumbnail_url": "", "site_name": ""}
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

        def og(prop: str) -> str:
            tag = soup.find("meta", property=f"og:{prop}") or soup.find("meta", attrs={"name": f"og:{prop}"})
            return (tag.get("content") or "").strip() if tag else ""

        result["title"] = og("title") or _text(soup, "title")
        result["description"] = og("description") or _meta(soup, "description")
        result["thumbnail_url"] = og("image")
        result["site_name"] = og("site_name")
    except Exception:
        pass
    return result


def _text(soup: BeautifulSoup, selector: str) -> str:
    tag = soup.find(selector)
    return tag.get_text(strip=True) if tag else ""


def _meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name})
    return (tag.get("content") or "").strip() if tag else ""
