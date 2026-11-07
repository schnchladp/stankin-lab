# src/binary_numbers/sources.py
"""Источники текста для поиска: файл на диске и веб-страница по URL"""

import re
from html.parser import HTMLParser
from pathlib import Path

import requests

DEFAULT_TIMEOUT = 10  # секунд ожидания ответа сервера
_USER_AGENT = "binary-numbers-lab/1.0"

# http:// или https://, затем хотя бы один символ имени хоста, без пробелов
_URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*\Z", re.IGNORECASE)


def is_valid_url(url: str) -> bool:
    """Проверяет, что строка похожа на адрес http:// или https://

    Examples:
        >>> is_valid_url("https://example.com/page?x=1")
        True
        >>> is_valid_url("ftp://example.com")
        False
    """
    return isinstance(url, str) and _URL_RE.match(url) is not None


def read_file(path: str | Path, encoding: str = "utf-8-sig") -> str:
    """Читает текстовый файл целиком

    Кодировка по умолчанию utf-8-sig: читает и обычный UTF-8, и UTF-8
    с BOM

    Raises:
        FileNotFoundError: файла нет
        UnicodeDecodeError: содержимое не в указанной кодировке
        OSError: другие ошибки доступа к файлу (в том числе каталог)
    """
    return Path(path).read_text(encoding=encoding)


class _TextExtractor(HTMLParser):
    """Собирает видимый текст HTML, пропуская script, style и noscript."""

    _SKIPPED_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)  # &lt; -> <, &amp; -> &
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIPPED_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def extract_visible_text(html: str) -> str:
    """Убирает из HTML теги, скрипты, стили и комментарии.

    Без этого регулярное выражение «находило» бы двоичные числа в
    атрибутах и коде страницы (width="100", z-index: 1101 и т. п.).

    Examples:
        >>> extract_visible_text("<p>код <b>101</b></p><script>1010</script>")
        'код 101'
    """
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return " ".join(parser.get_text().split())  # лишние пробелы -> один


def fetch_page_text(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Скачивает страницу по URL и возвращает её текст.

    Для HTML-страниц возвращается только видимый текст, для остальных
    типов (text/plain и др.) — содержимое как есть.

    Raises:
        ValueError: некорректный URL.
        requests.RequestException: сетевые ошибки, таймаут, HTTP-статус
            4xx/5xx.
    """
    if not is_valid_url(url):
        raise ValueError(f"некорректный URL: {url!r}")

    response = requests.get(
        url, timeout=timeout, headers={"User-Agent": _USER_AGENT}
    )
    response.raise_for_status()  # 4xx/5xx -> requests.HTTPError

    # Если сервер не указал кодировку, requests берёт ISO-8859-1 и русский
    # текст превращается в «кракозябры» — определяем кодировку по содержимому.
    if response.encoding is None or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding

    text = response.text
    if "html" in response.headers.get("Content-Type", "").lower():
        text = extract_visible_text(text)
    return text
