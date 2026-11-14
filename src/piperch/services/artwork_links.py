"""统一识别作品简介链接，保留原始 href 供前端查表改写。"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from piperch.domain.sources import ArtworkSource

_PIXIV_ARTWORK_PATH_PATTERN = re.compile(r"/(?:[a-z]{2}(?:-[a-z]{2})?/)?artworks/([0-9]+)/?", re.IGNORECASE)
_FANBOX_POST_URL_PATTERNS = (
    # 作者子域名投稿链接。
    re.compile(
        r"https?://(?!(?:www|api|downloads|accounts|print)\.)"
        r"[a-z0-9_-]+\.fanbox\.cc/posts/([0-9]+)/?",
    ),
    # 主域名 @作者投稿链接。
    re.compile(r"https?://(?:www\.)?fanbox\.cc/@[a-zA-Z0-9_-]+/posts/([0-9]+)/?"),
    # 旧版 Pixiv 投稿链接。
    re.compile(r"https?://(?:www\.)?pixiv\.net/fanbox/creator/[0-9]+/post/([0-9]+)/?"),
    # 投稿管理链接。
    re.compile(r"https?://(?:www\.)?fanbox\.cc/manage/posts/([0-9]+)/?"),
)


def _positive_safe_id(value: str | None) -> int | None:
    if value is None or re.fullmatch(r"[0-9]+", value) is None:
        return None
    digits = value.lstrip("0")
    if not digits or len(digits) > 16:
        return None
    number = int(digits)
    return number if number <= 2**53 - 1 else None


def _artwork_reference_from_url(value: str) -> tuple[ArtworkSource, int] | None:
    """支持 Pixiv 绝对、相对作品路径及 illust_id 旧式链接，以及四种 FANBOX 投稿链接。"""
    try:
        url = urlsplit(urljoin("https://www.pixiv.net", value))
        _ = url.port
    except ValueError:
        return None
    if url.scheme not in {"http", "https"}:
        return None
    hostname = url.hostname or ""
    if hostname == "pixiv.net" or hostname.endswith(".pixiv.net"):
        match = _PIXIV_ARTWORK_PATH_PATTERN.fullmatch(url.path)
        if match is not None:
            remote_id = _positive_safe_id(match[1])
            return (ArtworkSource.PIXIV, remote_id) if remote_id is not None else None
        if url.path.lower().endswith("/member_illust.php"):
            remote_id = _positive_safe_id(parse_qs(url.query, keep_blank_values=True).get("illust_id", [None])[0])
            return (ArtworkSource.PIXIV, remote_id) if remote_id is not None else None

    post_url = f"{url.scheme}://{hostname}{url.path}"
    for pattern in _FANBOX_POST_URL_PATTERNS:
        match = pattern.fullmatch(post_url)
        if match is not None:
            remote_id = _positive_safe_id(match[1])
            return (ArtworkSource.FANBOX, remote_id) if remote_id is not None else None
    return None


class _ArtworkLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: dict[ArtworkSource, dict[str, int]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = next((value for name, value in attrs if name == "href"), None)
        if href is None or (reference := _artwork_reference_from_url(href)) is None:
            return
        source, remote_id = reference
        # HTMLParser 与前端读取 href 时都会解码 HTML 实体，保留相同的映射键。
        self.links.setdefault(source, {})[href] = remote_id


def parse_artwork_links(document: str) -> dict[ArtworkSource, dict[str, int]]:
    """按来源收集简介中可识别的作品链接及原始作品 ID。"""
    parser = _ArtworkLinkParser()
    parser.feed(document)
    return parser.links
