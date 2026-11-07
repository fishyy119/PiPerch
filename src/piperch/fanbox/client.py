"""通过公开归档读取 FANBOX 作者、投稿和图片，不关联登录账号。"""

from __future__ import annotations

import asyncio
import time
import unicodedata
from typing import TYPE_CHECKING, cast
from urllib.parse import urlsplit

from piperch.domain.discovery import AuthorSummary, DiscoveryResult
from piperch.errors import UpstreamError
from piperch.fanbox.parsing import (
    as_mapping,
    as_text,
    image_attachments,
    parse_artwork,
    parse_candidate,
    parse_total_pages,
    positive_id,
)
from piperch.fanbox.transport import FanboxTransport

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from piperch.domain.artworks import RemoteArtwork

_PAGE_SIZE = 50


class FanboxClient:
    def __init__(self, *, proxy_url: str | None, request_interval_ms: int) -> None:
        self._transport = FanboxTransport(proxy_url=proxy_url, request_interval_ms=request_interval_ms)
        self._index_lock = asyncio.Lock()
        self._creators: list[tuple[AuthorSummary, str]] | None = None
        self._creators_expire_at = 0.0

    async def reconfigure(self, proxy_url: str | None, request_interval_ms: int) -> None:
        await self._transport.reconfigure(proxy_url, request_interval_ms)

    async def close(self) -> None:
        await self._transport.close()

    async def search_creators(self, query: str) -> list[AuthorSummary]:
        # 站点提供完整作者索引，缓存名称和公开账号名，仅返回匹配的 FANBOX 作者。
        async with self._index_lock:
            if self._creators is None or time.monotonic() >= self._creators_expire_at:
                values = await self._transport.get_json("/creators")
                if not isinstance(values, list):
                    raise UpstreamError("invalid_fanbox_response", "FANBOX 作者索引格式无效。")
                self._creators = [
                    (
                        AuthorSummary(positive_id(row.get("id")), as_text(row.get("name")), None),
                        unicodedata.normalize(
                            "NFKC", f"{as_text(row.get('name'))} {as_text(row.get('public_id'))}"
                        ).casefold(),
                    )
                    for value in cast("list[object]", values)
                    if (row := as_mapping(value)).get("service") == "fanbox" and positive_id(row.get("id"))
                ]
                self._creators_expire_at = time.monotonic() + 1800
        needle = unicodedata.normalize("NFKC", query).casefold().strip()
        return [user for user, names in self._creators if needle in names][:100]

    async def _profile(self, author_id: int) -> Mapping[str, object]:
        profile = as_mapping(await self._transport.get_json(f"/fanbox/user/{author_id}/profile"))
        if positive_id(profile.get("id")) != author_id or profile.get("service") != "fanbox":
            raise UpstreamError("invalid_fanbox_response", "FANBOX 作者信息无效。")
        return profile

    async def _posts(self, author_id: int, page: int) -> Sequence[object]:
        values = await self._transport.get_json(f"/fanbox/user/{author_id}?o={page * _PAGE_SIZE}")
        if not isinstance(values, list):
            raise UpstreamError("invalid_fanbox_response", "FANBOX 投稿列表格式无效。")
        return cast("list[object]", values)

    async def discover_user(self, author_id: int, page: int) -> DiscoveryResult:
        profile = await self._profile(author_id)
        # 页码与原站保持一致，图片筛选仅作用于本页。
        posts = await self._posts(author_id, page)
        document = await self._transport.get_text(f"/fanbox/user/{author_id}?o={page * _PAGE_SIZE}")
        total_pages = parse_total_pages(document, _PAGE_SIZE)
        name = as_text(profile.get("name")) or str(author_id)
        candidates = [
            item for value in posts if (item := parse_candidate(as_mapping(value), author_id, name)) is not None
        ]
        has_next_page = page + 1 < total_pages if total_pages is not None else len(posts) == _PAGE_SIZE
        return DiscoveryResult(candidates, page + 1 if has_next_page else None, total_pages)

    async def list_user_artwork_ids(self, author_id: int) -> list[int]:
        await self._profile(author_id)
        output: dict[int, None] = {}
        for page in range(2000):
            posts = await self._posts(author_id, page)
            for value in posts:
                post = as_mapping(value)
                if (
                    post.get("service") == "fanbox"
                    and positive_id(post.get("user")) == author_id
                    and image_attachments(post)
                    and (post_id := positive_id(post.get("id")))
                ):
                    output.setdefault(post_id, None)
            if len(posts) < _PAGE_SIZE:
                return list(output)
        raise UpstreamError("fanbox_post_limit", "该作者的投稿数量过多，请分批选择。")

    async def get_artwork(self, author_id: int, remote_id: int) -> RemoteArtwork:
        post = as_mapping(await self._transport.get_json(f"/fanbox/user/{author_id}/post/{remote_id}"))
        profile = await self._profile(author_id)
        return parse_artwork(post, profile, author_id, remote_id)

    async def list_artwork_preview_urls(self, author_id: int, remote_id: int) -> list[str]:
        artwork = await self.get_artwork(author_id, remote_id)
        return [f"https://img.pawchive.pw/thumbnail{urlsplit(url).path}" for url in artwork.original_urls]

    async def fetch_thumbnail(self, url: str) -> tuple[bytes, str]:
        return await self._transport.fetch_thumbnail(url)

    async def download(self, url: str, target: Path) -> tuple[str, int]:
        try:
            return await self._transport.download(url, target)
        except UpstreamError as error:
            if error.code != "fanbox_image_not_found" or not urlsplit(url).path.startswith("/data/"):
                raise
        # 归档状态可能滞后，仅在原图确实缺失时回退到对应预览图。
        preview_url = f"https://img.pawchive.pw/thumbnail{urlsplit(url).path}"
        return await self._transport.download(preview_url, target)
