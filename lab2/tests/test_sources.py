# tests/test_sources.py
"""Тесты чтения файла и загрузки веб-страницы (сеть подменена mock-ом)"""

from unittest.mock import MagicMock

import pytest
import requests

from binary_numbers import sources
from binary_numbers.sources import (
    extract_visible_text,
    fetch_page_text,
    is_valid_url,
    read_file,
)


# файл

def test_read_file(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("числа 101 и 11", encoding="utf-8")
    assert read_file(path) == "числа 101 и 11"


def test_read_file_accepts_str_path(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("1", encoding="utf-8")
    assert read_file(str(path)) == "1"


def test_read_file_with_bom(tmp_path):
    path = tmp_path / "bom.txt"
    path.write_bytes("﻿101".encode("utf-8"))
    assert read_file(path) == "101"


def test_read_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_file(tmp_path / "нет.txt")


def test_read_file_wrong_encoding(tmp_path):
    path = tmp_path / "cp1251.txt"
    path.write_bytes("привет 101".encode("cp1251"))
    with pytest.raises(UnicodeDecodeError):
        read_file(path)


def test_read_file_directory(tmp_path):
    with pytest.raises(OSError):
        read_file(tmp_path)


# URL

@pytest.mark.parametrize(
    "url",
    ["http://a.ru", "https://example.com/p?x=1#y", "HTTP://EXAMPLE.COM",
     "http://localhost:8000/demo.html"],
)
def test_valid_urls(url):
    assert is_valid_url(url)


@pytest.mark.parametrize(
    "url",
    ["", "example.com", "ftp://a.ru", "http://", "https:// a.ru",
     "http://a b.ru", "https://a.ru\n", None, 5],
)
def test_invalid_urls(url):
    assert not is_valid_url(url)


# HTML

def test_extract_visible_text_skips_scripts_and_styles():
    html = (
        "<html><head><style>a{z-index:1101}</style></head>"
        "<body><p>число <b>101</b></p><script>var x=1010;</script>"
        '<img width="100"></body></html>'
    )
    text = extract_visible_text(html)
    assert "101" in text
    assert "1010" not in text and "1101" not in text and "100" not in text


def test_extract_visible_text_entities():
    assert extract_visible_text("<p>1 &lt; 10 &amp; 11</p>") == "1 < 10 & 11"


def test_extract_visible_text_nested_noscript():
    html = "<noscript><script>1</script>0</noscript>11"
    assert extract_visible_text(html) == "11"


def test_extract_visible_text_stray_end_tag():
    assert extract_visible_text("</script>101") == "101"


# fetch_page_text (requests.get подменён)

def _response(text="", content_type="text/html", encoding="utf-8",
              apparent="utf-8", status_error=None):
    resp = MagicMock()
    resp.text = text
    resp.headers = {"Content-Type": content_type}
    resp.encoding = encoding
    resp.apparent_encoding = apparent
    if status_error:
        resp.raise_for_status.side_effect = status_error
    return resp


def test_fetch_html(monkeypatch):
    resp = _response("<p>101</p><script>11</script>")
    get = MagicMock(return_value=resp)
    monkeypatch.setattr(sources.requests, "get", get)
    assert fetch_page_text("https://example.com") == "101"
    kwargs = get.call_args.kwargs
    assert kwargs["timeout"] == sources.DEFAULT_TIMEOUT
    assert "User-Agent" in kwargs["headers"]


def test_fetch_plain_text_not_stripped(monkeypatch):
    resp = _response("1 < 10", content_type="text/plain")
    monkeypatch.setattr(sources.requests, "get", MagicMock(return_value=resp))
    assert fetch_page_text("http://a.ru") == "1 < 10"


def test_fetch_fixes_latin1_encoding(monkeypatch):
    resp = _response("x", encoding="ISO-8859-1", apparent="utf-8")
    monkeypatch.setattr(sources.requests, "get", MagicMock(return_value=resp))
    fetch_page_text("http://a.ru")
    assert resp.encoding == "utf-8"


def test_fetch_fixes_missing_encoding(monkeypatch):
    resp = _response("x", encoding=None, apparent="windows-1251")
    monkeypatch.setattr(sources.requests, "get", MagicMock(return_value=resp))
    fetch_page_text("http://a.ru")
    assert resp.encoding == "windows-1251"


def test_fetch_keeps_declared_encoding(monkeypatch):
    resp = _response("x", encoding="windows-1251", apparent="utf-8")
    monkeypatch.setattr(sources.requests, "get", MagicMock(return_value=resp))
    fetch_page_text("http://a.ru")
    assert resp.encoding == "windows-1251"


def test_fetch_invalid_url_does_not_call_network(monkeypatch):
    get = MagicMock()
    monkeypatch.setattr(sources.requests, "get", get)
    with pytest.raises(ValueError):
        fetch_page_text("not a url")
    get.assert_not_called()


def test_fetch_http_error(monkeypatch):
    resp = _response(status_error=requests.HTTPError("404"))
    monkeypatch.setattr(sources.requests, "get", MagicMock(return_value=resp))
    with pytest.raises(requests.HTTPError):
        fetch_page_text("http://a.ru/missing")


@pytest.mark.parametrize("exc", [requests.Timeout, requests.ConnectionError])
def test_fetch_network_errors_propagate(monkeypatch, exc):
    monkeypatch.setattr(
        sources.requests, "get", MagicMock(side_effect=exc("boom"))
    )
    with pytest.raises(requests.RequestException):
        fetch_page_text("http://a.ru")
