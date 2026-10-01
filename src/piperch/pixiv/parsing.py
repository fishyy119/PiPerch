from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from piperch.domain import ArtworkType, DiscoveryCandidate

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_ARTWORK_URL_PATTERN = re.compile(r"(?:artworks/|illust_id=)(\d+)", re.IGNORECASE)


def parse_artwork_ids(values: Sequence[str]) -> list[int]:
    output: dict[int, None] = {}
    for raw in values:
        for token in re.split(r"[\s,;]+", raw.strip()):
            match = _ARTWORK_URL_PATTERN.search(token)
            value = token if token.isdecimal() else match.group(1) if match else ""
            artwork_id = int(value) if value else 0
            if artwork_id > 0:
                output[artwork_id] = None
    return list(output)


def parse_pixiv_user_id(cookie: str | None) -> int | None:
    """从 PHPSESSID 的非敏感前缀读取当前登录用户 ID。"""
    if not cookie:
        return None
    for part in cookie.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name.casefold() == "phpsessid":
            prefix, underscore, _ = value.partition("_")
            if underscore and prefix.isdecimal() and (user_id := int(prefix)) > 0:
                return user_id
    return None


def as_mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, dict) else {}


def as_sequence(value: object) -> Sequence[object]:
    return cast("Sequence[object]", value) if isinstance(value, list) else ()


def as_text(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def as_integer(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def as_optional_integer(value: object) -> int | None:
    number = as_integer(value)
    return number if number > 0 else None


def artwork_type(value: object) -> ArtworkType:
    return {
        1: ArtworkType.MANGA,
        2: ArtworkType.UGOIRA,
    }.get(as_integer(value), ArtworkType.ILLUST)


def candidate_from_artwork_body(
    artwork_id: int,
    body: Mapping[str, object],
) -> DiscoveryCandidate:
    urls = as_mapping(body.get("urls"))
    return DiscoveryCandidate(
        artwork_id=artwork_id,
        title=as_text(body.get("illustTitle")) or as_text(body.get("title")) or f"作品 {artwork_id}",
        author_name=as_text(body.get("userName")) or "未知作者",
        artwork_type=artwork_type(body.get("illustType")),
        page_count=max(1, as_integer(body.get("pageCount"), 1)),
        x_restrict=max(0, as_integer(body.get("xRestrict"))),
        is_ai=as_integer(body.get("aiType")) >= 2,
        thumbnail_url=as_text(urls.get("regular")) or as_text(urls.get("small")) or None,
    )


def candidate_from_mapping(
    item: Mapping[str, object],
    *,
    default_artwork_id: int = 0,
) -> DiscoveryCandidate:
    artwork_id = as_integer(item.get("id"), default_artwork_id)
    thumbnail_url = as_text(item.get("url"))
    if not thumbnail_url:
        pages = as_sequence(item.get("pages"))
        first_page = as_mapping(pages[0]) if pages else {}
        urls = as_mapping(first_page.get("urls"))
        # 部分 Pixiv 缩略图列表使用尺寸名称作为键，其他接口则直接提供 url。
        thumbnail_url = (
            as_text(urls.get("540x540")) or as_text(urls.get("360x360")) or as_text(urls.get("1200x1200_standard"))
        )
    return DiscoveryCandidate(
        artwork_id=artwork_id,
        title=as_text(item.get("title")) or f"作品 {artwork_id}",
        author_name=as_text(item.get("userName")) or "未知作者",
        artwork_type=artwork_type(item.get("illustType")),
        page_count=max(1, as_integer(item.get("pageCount"), 1)),
        x_restrict=max(0, as_integer(item.get("xRestrict"))),
        is_ai=as_integer(item.get("aiType")) >= 2,
        thumbnail_url=thumbnail_url or None,
    )
