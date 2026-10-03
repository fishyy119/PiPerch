from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import httpx

from piperch.domain import (
    ArtworkType,
    BookmarkFolder,
    BookmarkFolderKind,
    BookmarkFolderReference,
    BookmarkVisibility,
    DiscoveryCandidate,
    FavoriteSyncResult,
    FollowedUser,
    PublicBookmark,
    RecommendedUser,
    RemoteArtwork,
    RemoteBookmarkReference,
    TagRecord,
    UgoiraFrame,
    UserProfile,
)
from piperch.errors import ConflictError, UpstreamError
from piperch.pixiv.parsing import (
    artwork_type as _artwork_type,
)
from piperch.pixiv.parsing import (
    as_integer as _integer,
)
from piperch.pixiv.parsing import (
    as_mapping as _mapping,
)
from piperch.pixiv.parsing import (
    as_optional_integer as _optional_integer,
)
from piperch.pixiv.parsing import (
    as_sequence as _sequence,
)
from piperch.pixiv.parsing import (
    as_text as _text,
)
from piperch.pixiv.parsing import (
    candidate_from_artwork_body,
    candidate_from_mapping,
    parse_artwork_ids,
    parse_pixiv_user_id,
)
from piperch.pixiv.transport import PixivTransport

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


class PixivClient:
    """提供 Pixiv AJAX 协议所需的作品发现和元数据操作。"""

    def __init__(self, *, proxy_url: str | None, request_interval_ms: int) -> None:
        self._transport = PixivTransport(
            proxy_url=proxy_url,
            request_interval_ms=request_interval_ms,
        )
        self._bookmark_cache_lock = asyncio.Lock()
        self._bookmark_cache_cookie: str | None = None
        self._public_bookmarks: dict[int, PublicBookmark] = {}
        self._bookmark_cache_offset = 0
        self._bookmark_cache_total: int | None = None
        self._bookmark_cache_complete = False

    async def reconfigure(self, proxy_url: str | None, request_interval_ms: int) -> None:
        await self._transport.reconfigure(proxy_url, request_interval_ms)

    async def close(self) -> None:
        await self._transport.close()

    async def validate_cookie(self, cookie: str | None) -> bool:
        if not cookie:
            return False
        try:
            await self._transport.get_body("/ajax/user/extra", cookie=cookie, params={"lang": "zh"})
        except UpstreamError:
            return False
        return True

    async def discover_artworks(
        self,
        inputs: Sequence[str],
        page: int,
        cookie: str | None,
        *,
        page_size: int = 24,
    ) -> tuple[list[DiscoveryCandidate], int | None]:
        artwork_ids = parse_artwork_ids(inputs)
        start = page * page_size
        selected = artwork_ids[start : start + page_size]
        candidates = [
            candidate_from_artwork_body(
                artwork_id,
                _mapping(await self._transport.get_body(f"/ajax/illust/{artwork_id}", cookie=cookie)),
            )
            for artwork_id in selected
        ]
        next_page = page + 1 if start + page_size < len(artwork_ids) else None
        return candidates, next_page

    async def discover_recommended_artworks(
        self,
        cookie: str | None,
    ) -> list[DiscoveryCandidate]:
        """读取当前账号的发现作品流，并按推荐顺序去重。"""
        self._require_current_user_id(cookie)
        body = _mapping(
            await self._transport.get_body(
                "/ajax/discovery/artworks",
                cookie=cookie,
                params={"mode": "all", "limit": 100, "lang": "zh"},
            )
        )
        candidates_by_id: dict[int, DiscoveryCandidate] = {}
        thumbnails = _mapping(body.get("thumbnails"))
        for raw_thumbnail in _sequence(thumbnails.get("illust")):
            thumbnail = _mapping(raw_thumbnail)
            artwork_id = _integer(thumbnail.get("id"))
            if artwork_id <= 0:
                continue
            candidates_by_id.setdefault(
                artwork_id,
                candidate_from_mapping(thumbnail, default_artwork_id=artwork_id),
            )

        ordered: dict[int, DiscoveryCandidate] = {}
        for raw_recommendation in _sequence(body.get("recommendedIllusts")):
            recommendation = _mapping(raw_recommendation)
            artwork_id = _integer(
                recommendation.get("illustId"),
                _integer(raw_recommendation),
            )
            candidate = candidates_by_id.get(artwork_id)
            if candidate is not None:
                ordered.setdefault(artwork_id, candidate)
        return list(ordered.values())

    async def discover_follow_updates(
        self,
        page: int,
        cookie: str | None,
    ) -> tuple[list[DiscoveryCandidate], int | None]:
        """按 Pixiv 返回顺序读取关注作者的最近更新。"""
        self._require_current_user_id(cookie)
        body = _mapping(
            await self._transport.get_body(
                "/ajax/follow_latest/illust",
                cookie=cookie,
                params={"p": page + 1, "mode": "all", "lang": "zh"},
            )
        )
        thumbnails = _mapping(body.get("thumbnails"))
        candidates: dict[int, DiscoveryCandidate] = {}
        for raw_thumbnail in _sequence(thumbnails.get("illust")):
            thumbnail = _mapping(raw_thumbnail)
            artwork_id = _integer(thumbnail.get("id"))
            if artwork_id <= 0:
                continue
            candidates.setdefault(
                artwork_id,
                candidate_from_mapping(thumbnail, default_artwork_id=artwork_id),
            )

        is_last_page = _mapping(body.get("page")).get("isLastPage")
        next_page = page + 1 if candidates and is_last_page is False else None
        return list(candidates.values()), next_page

    async def discover_recommended_users(
        self,
        cookie: str | None,
    ) -> list[RecommendedUser]:
        """读取当前账号的推荐作者，并关联作者资料与近期插画。"""
        self._require_current_user_id(cookie)
        body = _mapping(
            await self._transport.get_body(
                "/ajax/discovery/users",
                cookie=cookie,
                params={"limit": 20, "lang": "zh"},
            )
        )

        users_by_id: dict[int, Mapping[str, object]] = {}
        for raw_user in _sequence(body.get("users")):
            user = _mapping(raw_user)
            user_id = _integer(user.get("userId"))
            if user_id > 0:
                users_by_id.setdefault(user_id, user)

        artworks_by_id: dict[int, DiscoveryCandidate] = {}
        thumbnails = _mapping(body.get("thumbnails"))
        for raw_thumbnail in _sequence(thumbnails.get("illust")):
            thumbnail = _mapping(raw_thumbnail)
            artwork_id = _integer(thumbnail.get("id"))
            if artwork_id > 0:
                artworks_by_id.setdefault(
                    artwork_id,
                    candidate_from_mapping(thumbnail, default_artwork_id=artwork_id),
                )

        recommended: dict[int, RecommendedUser] = {}
        for raw_recommendation in _sequence(body.get("recommendedUsers")):
            recommendation = _mapping(raw_recommendation)
            user_id = _integer(recommendation.get("userId"))
            user = users_by_id.get(user_id)
            if user_id <= 0 or user is None:
                continue
            artworks = tuple(
                artwork
                for raw_artwork_id in _sequence(recommendation.get("recentIllustIds"))
                if (artwork := artworks_by_id.get(_integer(raw_artwork_id))) is not None
            )
            recommended.setdefault(
                user_id,
                RecommendedUser(
                    user_id=user_id,
                    name=_text(user.get("name")) or f"用户 {user_id}",
                    comment=_text(user.get("comment")),
                    avatar_url=_text(user.get("imageBig")) or _text(user.get("image")) or None,
                    is_followed=user.get("isFollowed") is True,
                    artworks=artworks,
                ),
            )
        return list(recommended.values())

    async def follow_user(self, user_id: int, cookie: str | None) -> None:
        """使用当前账号公开关注指定作者。"""
        self._require_current_user_id(cookie)
        await self._transport.post_form(
            "/bookmark_add.php",
            cookie=cookie,
            data={
                "mode": "add",
                "type": "user",
                "user_id": user_id,
                "tag": "",
                "restrict": 0,
                "format": "json",
            },
        )

    async def unfollow_user(self, user_id: int, cookie: str | None) -> None:
        """取消当前账号对指定作者的关注。"""
        self._require_current_user_id(cookie)
        await self._transport.post_form(
            "/rpc_group_setting.php",
            cookie=cookie,
            data={
                "mode": "del",
                "type": "bookuser",
                "id": user_id,
            },
        )

    async def get_user_profile(self, user_id: int, cookie: str | None) -> UserProfile:
        """读取作者头像和当前账号的关注状态。"""
        body = _mapping(
            await self._transport.get_body(
                f"/ajax/user/{user_id}",
                cookie=cookie,
                params={"full": 1, "lang": "zh"},
            )
        )
        return UserProfile(
            avatar_url=(
                _text(body.get("imageBig")) or _text(body.get("image")) or _text(body.get("profileImageUrl")) or None
            ),
            is_followed=body.get("isFollowed") is True if parse_pixiv_user_id(cookie) is not None else None,
        )

    async def list_artwork_preview_urls(
        self,
        artwork_id: int,
        cookie: str | None,
    ) -> list[str]:
        """按作品页顺序读取适合快速预览的图片地址。"""
        pages = _sequence(
            await self._transport.get_body(
                f"/ajax/illust/{artwork_id}/pages",
                cookie=cookie,
            )
        )
        preview_urls: list[str] = []
        for raw_page in pages:
            urls = _mapping(_mapping(raw_page).get("urls"))
            preview_url = _text(urls.get("regular")) or _text(urls.get("small"))
            if preview_url:
                preview_urls.append(preview_url)
        return preview_urls

    async def discover_user(
        self,
        user_id: int,
        page: int,
        cookie: str | None,
        *,
        page_size: int = 48,
    ) -> tuple[list[DiscoveryCandidate], int | None]:
        ordered = await self.list_user_artwork_ids(user_id, cookie)
        start = page * page_size
        selected = ordered[start : start + page_size]
        if not selected:
            return [], None

        # 用户主页只返回作品 ID，预览所需的卡片元数据可以一次批量取得。逐个读取完整作品
        # 会为每项额外请求详情和分页数据，在默认限速下单页需要一分钟左右。
        params = httpx.QueryParams({"ids[]": tuple(str(artwork_id) for artwork_id in selected), "lang": "zh"})
        cards = _mapping(
            await self._transport.get_body(
                f"/ajax/user/{user_id}/illusts",
                cookie=cookie,
                params=params,
            )
        )
        candidates = [
            candidate_from_mapping(card, default_artwork_id=artwork_id)
            for artwork_id in selected
            if (card := _mapping(cards.get(str(artwork_id))))
        ]
        next_page = page + 1 if start + page_size < len(ordered) else None
        return candidates, next_page

    async def list_user_artwork_ids(self, user_id: int, cookie: str | None) -> list[int]:
        """读取作者全部插画和漫画 ID，不为每个作品请求详情。"""
        body = _mapping(await self._transport.get_body(f"/ajax/user/{user_id}/profile/all", cookie=cookie))
        ids = {
            *(_integer(key) for key in _mapping(body.get("illusts"))),
            *(_integer(key) for key in _mapping(body.get("manga"))),
        }
        return sorted((item for item in ids if item > 0), reverse=True)

    async def list_followed_users(self, cookie: str | None) -> list[FollowedUser]:
        """读取当前账号公开与非公开关注的作者，并按 Pixiv 返回顺序去重。"""
        own_user_id = parse_pixiv_user_id(cookie)
        if own_user_id is None:
            raise UpstreamError(
                "pixiv_cookie_required",
                "请先在设置中保存包含 PHPSESSID 的 Pixiv Cookie。",
                401,
            )

        followed: dict[int, FollowedUser] = {}
        page_size = 100
        for visibility in ("show", "hide"):
            offset = 0
            for _ in range(100):
                body = _mapping(
                    await self._transport.get_body(
                        f"/ajax/user/{own_user_id}/following",
                        cookie=cookie,
                        params={
                            "offset": offset,
                            "limit": page_size,
                            "rest": visibility,
                            "tag": "",
                            "acceptingRequests": 0,
                            "lang": "zh",
                        },
                    )
                )
                raw_users = _sequence(body.get("users"))
                for raw in raw_users:
                    user = _mapping(raw)
                    user_id = _integer(user.get("userId"))
                    if user_id <= 0:
                        continue
                    followed.setdefault(
                        user_id,
                        FollowedUser(
                            user_id=user_id,
                            name=_text(user.get("userName")) or f"用户 {user_id}",
                            avatar_url=_text(user.get("profileImageUrl")) or None,
                        ),
                    )
                offset += len(raw_users)
                total = max(0, _integer(body.get("total")))
                if not raw_users or offset >= total:
                    break
            else:
                raise UpstreamError("following_too_many_pages", "关注作者分页数量超出安全上限。")
        return list(followed.values())

    async def list_bookmark_folders(self, cookie: str | None) -> list[BookmarkFolder]:
        """读取当前账号公开与非公开的插画收藏标签。"""
        user_id = self._require_current_user_id(cookie)
        tag_groups = _mapping(
            await self._transport.get_body(
                f"/ajax/user/{user_id}/illusts/bookmark/tags",
                cookie=cookie,
                params={"lang": "zh"},
            )
        )
        folders: list[BookmarkFolder] = []
        for visibility in (BookmarkVisibility.PUBLIC, BookmarkVisibility.PRIVATE):
            body = await self._bookmark_page(
                user_id,
                BookmarkFolderReference(visibility, None),
                0,
                1,
                cookie,
            )
            folders.append(
                BookmarkFolder(
                    reference=BookmarkFolderReference(visibility, None),
                    kind=BookmarkFolderKind.ALL,
                    name="全部收藏",
                    item_count=max(0, _integer(body.get("total"))),
                )
            )

            tags: list[tuple[str, int]] = []
            group_name = "public" if visibility is BookmarkVisibility.PUBLIC else "private"
            for raw_tag in _sequence(tag_groups.get(group_name)):
                tag = _mapping(raw_tag)
                name = _text(tag.get("tag")) or _text(tag.get("name"))
                if name:
                    count = _integer(tag.get("cnt"), _integer(tag.get("count")))
                    tags.append((name, max(0, count)))

            uncategorized = next(
                ((name, count) for name, count in tags if name in {"未分類", "未分类"}),
                ("未分類", 0),
            )
            folders.append(
                BookmarkFolder(
                    reference=BookmarkFolderReference(visibility, uncategorized[0]),
                    kind=BookmarkFolderKind.UNCATEGORIZED,
                    name="未分类",
                    item_count=uncategorized[1],
                )
            )
            folders.extend(
                BookmarkFolder(
                    reference=BookmarkFolderReference(visibility, name),
                    kind=BookmarkFolderKind.TAG,
                    name=name,
                    item_count=count,
                )
                for name, count in tags
                if name not in {"未分類", "未分类"}
            )
        return folders

    async def discover_bookmarks(
        self,
        folder: BookmarkFolderReference,
        page: int,
        cookie: str | None,
        *,
        page_size: int = 48,
    ) -> tuple[list[DiscoveryCandidate], int | None]:
        """按收藏标签读取当前账号的一页插画收藏。"""
        user_id = self._require_current_user_id(cookie)
        offset = page * page_size
        body = await self._bookmark_page(user_id, folder, offset, page_size, cookie)
        works = _sequence(body.get("works"))
        candidates = [
            candidate_from_mapping(work)
            for raw_work in works
            if (work := _mapping(raw_work)) and _integer(work.get("id")) > 0
        ]
        total = max(0, _integer(body.get("total")))
        next_page = page + 1 if works and (not total or offset + len(works) < total) else None
        return candidates, next_page

    async def list_bookmark_artwork_ids(
        self,
        folders: Sequence[BookmarkFolderReference],
        cookie: str | None,
        *,
        page_size: int = 100,
    ) -> list[int]:
        """按收藏夹顺序读取全部作品 ID，并在跨标签时去重。"""
        user_id = self._require_current_user_id(cookie)
        artwork_ids: dict[int, None] = {}
        for folder in folders:
            offset = 0
            for _ in range(1000):
                body = await self._bookmark_page(user_id, folder, offset, page_size, cookie)
                works = _sequence(body.get("works"))
                for raw_work in works:
                    artwork_id = _integer(_mapping(raw_work).get("id"))
                    if artwork_id > 0:
                        artwork_ids.setdefault(artwork_id, None)
                total = max(0, _integer(body.get("total")))
                offset += len(works)
                if not works or (total > 0 and offset >= total):
                    break
            else:
                raise UpstreamError(
                    "bookmark_too_many_pages",
                    "收藏分页数量超出安全上限。",
                )
        return list(artwork_ids)

    @staticmethod
    def _require_current_user_id(cookie: str | None) -> int:
        user_id = parse_pixiv_user_id(cookie)
        if user_id is None:
            raise UpstreamError(
                "pixiv_cookie_required",
                "请先在设置中保存包含 PHPSESSID 的 Pixiv Cookie。",
                401,
            )
        return user_id

    async def _bookmark_page(
        self,
        user_id: int,
        folder: BookmarkFolderReference,
        offset: int,
        limit: int,
        cookie: str | None,
    ) -> Mapping[str, object]:
        rest = "show" if folder.visibility is BookmarkVisibility.PUBLIC else "hide"
        return _mapping(
            await self._transport.get_body(
                f"/ajax/user/{user_id}/illusts/bookmarks",
                cookie=cookie,
                params={
                    "tag": folder.tag or "",
                    "offset": max(0, offset),
                    "limit": max(1, min(100, limit)),
                    "rest": rest,
                    "lang": "zh",
                },
            )
        )

    async def get_public_bookmark(
        self,
        artwork_id: int,
        bookmark_id: int,
        cookie: str | None,
    ) -> PublicBookmark:
        """按需扫描公开收藏页，读取一件作品的收藏标签。"""
        user_id = self._require_current_user_id(cookie)
        if cookie is None:
            raise UpstreamError("pixiv_cookie_required", "请先设置 Pixiv Cookie。", 401)
        async with self._bookmark_cache_lock:
            if cookie != self._bookmark_cache_cookie:
                self._reset_public_bookmark_cache(cookie)
            cached = self._public_bookmarks.get(artwork_id)
            if cached is not None and cached.bookmark_id == bookmark_id:
                return cached

            while not self._bookmark_cache_complete:
                body = await self._bookmark_page(
                    user_id,
                    BookmarkFolderReference(BookmarkVisibility.PUBLIC, None),
                    self._bookmark_cache_offset,
                    100,
                    cookie,
                )
                works = _sequence(body.get("works"))
                bookmark_tags = body.get("bookmarkTags")
                if not isinstance(bookmark_tags, (dict, list)) or (isinstance(bookmark_tags, list) and bookmark_tags):
                    raise UpstreamError("invalid_pixiv_response", "Pixiv 公开收藏标签结构无效。")
                tags_by_bookmark = _mapping(cast("object", bookmark_tags))
                for raw_work in works:
                    work = _mapping(raw_work)
                    work_id = _integer(work.get("id"))
                    reference = self._bookmark_reference(work.get("bookmarkData"))
                    if work_id <= 0 or reference is None or reference.private:
                        continue
                    raw_tags: object = []
                    has_tag_entry = False
                    for key, value in tags_by_bookmark.items():
                        if str(key) == str(reference.bookmark_id):
                            raw_tags = value
                            has_tag_entry = True
                            break
                    if has_tag_entry and not isinstance(raw_tags, list):
                        raise UpstreamError("invalid_pixiv_response", "Pixiv 公开收藏标签结构无效。")
                    parsed_tags: list[str] = []
                    for raw_tag in _sequence(cast("object", raw_tags)):
                        tag = raw_tag if isinstance(raw_tag, str) else _text(_mapping(raw_tag).get("tag"))
                        if not tag:
                            raise UpstreamError("invalid_pixiv_response", "Pixiv 公开收藏标签结构无效。")
                        parsed_tags.append(tag)
                    self._public_bookmarks[work_id] = PublicBookmark(
                        artwork_id=work_id,
                        bookmark_id=reference.bookmark_id,
                        tags=tuple(dict.fromkeys(parsed_tags)),
                    )

                self._bookmark_cache_offset += len(works)
                total = max(0, _integer(body.get("total")))
                self._bookmark_cache_total = total
                if not works or len(works) < 100 or (total > 0 and self._bookmark_cache_offset >= total):
                    self._bookmark_cache_complete = True
                cached = self._public_bookmarks.get(artwork_id)
                if cached is not None and cached.bookmark_id == bookmark_id:
                    return cached

            raise UpstreamError(
                "bookmark_tags_unavailable",
                "未能在 Pixiv 公开收藏中找到该作品的收藏标签。",
            )

    async def sync_public_bookmark(
        self,
        artwork_id: int,
        desired_tags: Sequence[str] | None,
        cookie: str | None,
    ) -> FavoriteSyncResult:
        """将一件作品的本地收藏状态收敛到 Pixiv 公开收藏。"""
        self._require_current_user_id(cookie)
        await self._invalidate_public_bookmark_cache()
        body = _mapping(await self._transport.get_body(f"/ajax/illust/{artwork_id}", cookie=cookie))
        reference = self._bookmark_reference(body.get("bookmarkData"))
        if reference is not None and reference.private:
            raise ConflictError("private_bookmark_conflict", "Pixiv 上存在私密收藏，无法用本地公开收藏覆盖。")

        if desired_tags is None:
            if reference is None:
                return FavoriteSyncResult(is_favorite=False, tags=())
            await self._transport.post_form(
                "/ajax/illusts/bookmarks/delete",
                cookie=cookie,
                data={"bookmark_id": reference.bookmark_id},
            )
            await self._invalidate_public_bookmark_cache()
            return FavoriteSyncResult(is_favorite=False, tags=())

        normalized_tags = tuple(dict.fromkeys(desired_tags))
        if reference is None:
            await self._transport.post_json(
                "/ajax/illusts/bookmarks/add",
                cookie=cookie,
                json_body={
                    "illust_id": str(artwork_id),
                    "restrict": 0,
                    "comment": "",
                    "tags": list(normalized_tags),
                },
            )
            await self._invalidate_public_bookmark_cache()
            return FavoriteSyncResult(is_favorite=True, tags=normalized_tags)

        bookmark = await self.get_public_bookmark(artwork_id, reference.bookmark_id, cookie)
        current_tags = set(bookmark.tags)
        desired_tag_set = set(normalized_tags)
        removed = [tag for tag in bookmark.tags if tag not in desired_tag_set]
        added = [tag for tag in normalized_tags if tag not in current_tags]
        if removed:
            await self._transport.post_json(
                "/ajax/illusts/bookmarks/remove_tags",
                cookie=cookie,
                json_body={
                    "removeTags": removed,
                    "bookmarkIds": [str(reference.bookmark_id)],
                },
            )
            await self._invalidate_public_bookmark_cache()
        if added:
            await self._transport.post_json(
                "/ajax/illusts/bookmarks/add_tags",
                cookie=cookie,
                json_body={
                    "tags": added,
                    "bookmarkIds": [str(reference.bookmark_id)],
                },
            )
            await self._invalidate_public_bookmark_cache()
        return FavoriteSyncResult(is_favorite=True, tags=normalized_tags)

    @staticmethod
    def _bookmark_reference(value: object) -> RemoteBookmarkReference | None:
        data = _mapping(value)
        bookmark_id = _integer(data.get("id"))
        if bookmark_id <= 0:
            return None
        raw_private = data.get("private")
        private = raw_private if isinstance(raw_private, bool) else _integer(raw_private) > 0
        return RemoteBookmarkReference(bookmark_id=bookmark_id, private=private)

    def _reset_public_bookmark_cache(self, cookie: str | None) -> None:
        self._bookmark_cache_cookie = cookie
        self._public_bookmarks.clear()
        self._bookmark_cache_offset = 0
        self._bookmark_cache_total = None
        self._bookmark_cache_complete = False

    async def _invalidate_public_bookmark_cache(self) -> None:
        async with self._bookmark_cache_lock:
            self._reset_public_bookmark_cache(None)

    async def discover_series(
        self,
        series_id: int,
        page: int,
        cookie: str | None,
    ) -> tuple[list[DiscoveryCandidate], int | None]:
        body = _mapping(
            await self._transport.get_body(
                f"/ajax/series/{series_id}",
                cookie=cookie,
                params={"p": page + 1, "lang": "zh"},
            )
        )
        page_data = _mapping(body.get("page"))
        entries = _sequence(page_data.get("series"))
        artwork_ids = [artwork_id for item in entries if (artwork_id := _integer(_mapping(item).get("workId"))) > 0]
        thumbnails = _sequence(_mapping(body.get("thumbnails")).get("illust"))
        cards = {
            artwork_id: card
            for raw in thumbnails
            if (card := _mapping(raw)) and (artwork_id := _integer(card.get("id"))) > 0
        }
        candidates = [
            candidate_from_mapping(cards[artwork_id], default_artwork_id=artwork_id)
            for artwork_id in artwork_ids
            if artwork_id in cards
        ]
        series_rows = _sequence(body.get("illustSeries"))
        total = _integer(_mapping(series_rows[0]).get("total")) if series_rows else 0
        next_page = page + 1 if entries and (not total or (page + 1) * 12 < total) else None
        return candidates, next_page

    async def get_artwork(self, artwork_id: int, cookie: str | None) -> RemoteArtwork:
        body = _mapping(await self._transport.get_body(f"/ajax/illust/{artwork_id}", cookie=cookie))
        artwork_type = _artwork_type(body.get("illustType"))
        pages_body = await self._transport.get_body(f"/ajax/illust/{artwork_id}/pages", cookie=cookie)
        original_urls = tuple(
            url
            for page in _sequence(pages_body)
            if (url := _text(_mapping(_mapping(page).get("urls")).get("original")))
        )

        frames: tuple[UgoiraFrame, ...] = ()
        ugoira_zip_url: str | None = None
        if artwork_type is ArtworkType.UGOIRA:
            ugoira = _mapping(await self._transport.get_body(f"/ajax/illust/{artwork_id}/ugoira_meta", cookie=cookie))
            ugoira_zip_url = _text(ugoira.get("originalSrc")) or _text(ugoira.get("src")) or None
            frames = tuple(
                UgoiraFrame(
                    file_name=_text(frame.get("file"), f"{index:06}.jpg"),
                    delay_ms=max(0, _integer(frame.get("delay"), 100)),
                )
                for index, raw in enumerate(_sequence(ugoira.get("frames")))
                if (frame := _mapping(raw))
            )

        tag_root = _mapping(body.get("tags"))
        parsed_tags = tuple(
            TagRecord(
                name=_text(tag.get("tag")),
                translated_name=_text(tag.get("translation")) or None,
            )
            for raw in _sequence(tag_root.get("tags"))
            if (tag := _mapping(raw)) and _text(tag.get("tag"))
        )
        series_data = _mapping(body.get("seriesNavData"))
        urls = _mapping(body.get("urls"))
        author_id = _optional_integer(body.get("userId"))
        if author_id is None:
            raise UpstreamError("invalid_pixiv_response", "Pixiv 作品数据缺少作者 ID。")
        return RemoteArtwork(
            artwork_id=artwork_id,
            artwork_type=artwork_type,
            title=_text(body.get("illustTitle")) or _text(body.get("title")) or f"作品 {artwork_id}",
            description=_text(body.get("description")),
            author_id=author_id,
            author_name=_text(body.get("userName")) or f"用户 {author_id}",
            author_account=_text(body.get("userAccount")) or None,
            author_avatar_url=None,
            series_id=_optional_integer(series_data.get("seriesId")),
            series_title=_text(series_data.get("title")) or None,
            page_count=max(1, _integer(body.get("pageCount"), len(original_urls) or 1)),
            width=_optional_integer(body.get("width")),
            height=_optional_integer(body.get("height")),
            x_restrict=max(0, _integer(body.get("xRestrict"))),
            is_ai=_integer(body.get("aiType")) >= 2,
            published_at=_text(body.get("createDate")) or None,
            original_urls=original_urls,
            thumbnail_url=_text(urls.get("regular")) or _text(urls.get("small")) or None,
            bookmark_data=self._bookmark_reference(body.get("bookmarkData")),
            ugoira_zip_url=ugoira_zip_url,
            ugoira_frames=frames,
            tags=parsed_tags,
        )

    async def fetch_thumbnail(self, url: str, cookie: str | None) -> tuple[bytes, str]:
        return await self._transport.fetch_thumbnail(url, cookie)

    async def download(self, url: str, target: Path, cookie: str | None) -> tuple[str, int]:
        return await self._transport.download(url, target, cookie)
