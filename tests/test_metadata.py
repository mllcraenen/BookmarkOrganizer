import pytest
import respx
import httpx

from core.metadata import fetch_metadata


OG_HTML = """
<html>
<head>
  <meta property="og:title" content="Test Title" />
  <meta property="og:description" content="Test description" />
  <meta property="og:image" content="https://example.com/img.jpg" />
  <meta property="og:site_name" content="Example" />
</head>
<body></body>
</html>
"""

MINIMAL_HTML = """
<html><head><title>Fallback Title</title>
<meta name="description" content="Fallback description" /></head><body></body></html>
"""

EMPTY_HTML = "<html><head></head><body></body></html>"


@respx.mock
def test_fetch_metadata_og_tags():
    respx.get("https://example.com/page").mock(
        return_value=httpx.Response(200, text=OG_HTML, headers={"content-type": "text/html"})
    )
    result = fetch_metadata("https://example.com/page")
    assert result["title"] == "Test Title"
    assert result["description"] == "Test description"
    assert result["thumbnail_url"] == "https://example.com/img.jpg"
    assert result["site_name"] == "Example"


@respx.mock
def test_fetch_metadata_fallback_to_title_and_meta():
    respx.get("https://example.com/minimal").mock(
        return_value=httpx.Response(200, text=MINIMAL_HTML, headers={"content-type": "text/html"})
    )
    result = fetch_metadata("https://example.com/minimal")
    assert result["title"] == "Fallback Title"
    assert result["description"] == "Fallback description"
    assert result["thumbnail_url"] == ""
    assert result["site_name"] == ""


@respx.mock
def test_fetch_metadata_empty_page():
    respx.get("https://example.com/empty").mock(
        return_value=httpx.Response(200, text=EMPTY_HTML, headers={"content-type": "text/html"})
    )
    result = fetch_metadata("https://example.com/empty")
    assert result == {"title": "", "description": "", "thumbnail_url": "", "site_name": ""}


@respx.mock
def test_fetch_metadata_http_error():
    respx.get("https://example.com/notfound").mock(return_value=httpx.Response(404))
    result = fetch_metadata("https://example.com/notfound")
    assert result == {"title": "", "description": "", "thumbnail_url": "", "site_name": ""}


@respx.mock
def test_fetch_metadata_network_error():
    respx.get("https://unreachable.example").mock(side_effect=httpx.ConnectError("refused"))
    result = fetch_metadata("https://unreachable.example")
    assert result == {"title": "", "description": "", "thumbnail_url": "", "site_name": ""}


@respx.mock
def test_fetch_metadata_returns_all_keys_on_partial():
    html = """<html><head><meta property="og:title" content="Only Title"/></head></html>"""
    respx.get("https://example.com/partial").mock(
        return_value=httpx.Response(200, text=html, headers={"content-type": "text/html"})
    )
    result = fetch_metadata("https://example.com/partial")
    assert result["title"] == "Only Title"
    assert result["description"] == ""
    assert result["thumbnail_url"] == ""
    assert result["site_name"] == ""
