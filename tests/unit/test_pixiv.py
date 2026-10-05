from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from piperch.domain import BookmarkFolderKind, BookmarkFolderReference, BookmarkVisibility
from piperch.errors import UpstreamError
from piperch.pixiv import PixivClient, parse_artwork_ids, parse_pixiv_user_id

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_parse_artwork_ids_supports_urls_and_deduplicates() -> None:
    result = parse_artwork_ids(
        [
            "123 456",
            "https://www.pixiv.net/artworks/123",
            "https://www.pixiv.net/member_illust.php?illust_id=789",
            (
                '<a href="https://www.pixiv.net/artworks/321">作品一</a>'
                '<a href="https://www.pixiv.net/artworks/654">作品二</a>'
            ),
            "invalid",
        ]
    )

    assert result == [123, 456, 789, 321, 654]


def test_parse_artwork_ids_rejects_non_positive_values() -> None:
    assert parse_artwork_ids(["0", "-1", "nothing"]) == []


def test_parse_pixiv_user_id_reads_phpsessid_prefix() -> None:
    assert parse_pixiv_user_id("foo=bar; PHPSESSID=12345_secret; baz=value") == 12345
    assert parse_pixiv_user_id("PHPSESSID=invalid") is None
    assert parse_pixiv_user_id(None) is None


@pytest.mark.asyncio
async def test_discovery_recommendations_follow_recommended_ids_and_ignore_missing_metadata() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(
            "https://www.pixiv.net/ajax/discovery/artworks",
            params={"mode": "all", "limit": 100, "lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "recommendedIllusts": [
                            {"illustId": "103", "recommendMethods": ["history"]},
                            {"illustId": "102", "recommendMethods": ["bookmark"]},
                            {"illustId": "103", "recommendMethods": ["history"]},
                            {"illustId": "404", "recommendMethods": []},
                            {"illustId": "invalid", "recommendMethods": []},
                        ],
                        "thumbnails": {
                            "illust": [
                                {"id": "102", "title": "第二件作品", "userName": "作者乙"},
                                {
                                    "id": "103",
                                    "title": "第一件作品",
                                    "illustType": 0,
                                    "pageCount": 1,
                                    "userName": "作者甲",
                                    "pages": [
                                        {
                                            "width": 1200,
                                            "height": 800,
                                            "urls": {
                                                "1200x1200_standard": "https://i.pximg.net/103-large.jpg",
                                                "540x540": "https://i.pximg.net/103-medium.jpg",
                                                "360x360": "https://i.pximg.net/103-small.jpg",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "id": "101",
                                    "title": "未被推荐的缩略图",
                                    "userName": "作者丙",
                                },
                                {"id": "invalid"},
                            ],
                            "novel": [
                                {
                                    "id": "999",
                                    "title": "小说",
                                }
                            ],
                        },
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            recommendations = await client.discover_recommended_artworks("PHPSESSID=42_secret")
        finally:
            await client.close()

    assert route.call_count == 1
    assert [item.artwork_id for item in recommendations] == [103, 102]
    assert recommendations[0].thumbnail_url == "https://i.pximg.net/103-medium.jpg"


@pytest.mark.asyncio
async def test_follow_updates_reads_ordered_pages_and_stops_at_last_page() -> None:
    with respx.mock(assert_all_called=True) as router:
        first_route = router.get(
            "https://www.pixiv.net/ajax/follow_latest/illust",
            params={"p": 1, "mode": "all", "lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "page": {"isLastPage": False},
                        "thumbnails": {
                            "illust": [
                                {"id": "103", "title": "最新作品", "userName": "作者甲"},
                                {"id": "102", "title": "稍早作品", "userName": "作者乙"},
                                {"id": "103", "title": "重复作品", "userName": "作者甲"},
                                {"id": "invalid"},
                            ]
                        },
                    },
                },
            )
        )
        last_route = router.get(
            "https://www.pixiv.net/ajax/follow_latest/illust",
            params={"p": 2, "mode": "all", "lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "page": {"isLastPage": True},
                        "thumbnails": {"illust": [{"id": "101", "title": "末页作品", "userName": "作者丙"}]},
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            first_page, first_next_page = await client.discover_follow_updates(0, "PHPSESSID=42_secret")
            last_page, last_next_page = await client.discover_follow_updates(1, "PHPSESSID=42_secret")
        finally:
            await client.close()

    assert first_route.call_count == 1
    assert last_route.call_count == 1
    assert [item.artwork_id for item in first_page] == [103, 102]
    assert first_next_page == 1
    assert [item.artwork_id for item in last_page] == [101]
    assert last_next_page is None


@pytest.mark.asyncio
async def test_cookie_validation_does_not_retry_forbidden_response() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(
            "https://www.pixiv.net/ajax/user/extra",
            params={"lang": "zh"},
        ).mock(return_value=httpx.Response(403))
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            valid = await client.validate_cookie("PHPSESSID=invalid")
        finally:
            await client.close()

    assert valid is False
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_cookie_validation_retries_rate_limit_and_respects_retry_after(
    monkeypatch: MonkeyPatch,
) -> None:
    delays: list[float] = []

    async def record_delay(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr("piperch.pixiv.transport.asyncio.sleep", record_delay)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(
            "https://www.pixiv.net/ajax/user/extra",
            params={"lang": "zh"},
        ).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "60"}),
                httpx.Response(200, json={"error": False, "body": {}}),
            ]
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            valid = await client.validate_cookie("PHPSESSID=valid")
        finally:
            await client.close()

    assert valid is True
    assert route.call_count == 2
    assert delays == [60]


@pytest.mark.asyncio
async def test_discover_user_fetches_preview_cards_in_one_batch() -> None:
    with respx.mock(assert_all_called=True) as router:
        profile_route = router.get(
            "https://www.pixiv.net/ajax/user/42/profile/all",
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "illusts": {"103": None, "101": None},
                        "manga": {"102": None},
                    },
                },
            )
        )
        cards_route = router.get(
            "https://www.pixiv.net/ajax/user/42/illusts",
            params=[("ids[]", "103"), ("ids[]", "102"), ("lang", "zh")],
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "103": {
                            "id": "103",
                            "title": "插画",
                            "illustType": 0,
                            "pageCount": 1,
                            "xRestrict": 0,
                            "aiType": 1,
                            "userName": "作者",
                        },
                        "102": {
                            "id": "102",
                            "title": "漫画",
                            "illustType": 1,
                            "pageCount": 3,
                            "xRestrict": 1,
                            "aiType": 2,
                            "userName": "作者",
                        },
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            candidates, next_page = await client.discover_user(
                42,
                0,
                "PHPSESSID=valid",
                page_size=2,
            )
        finally:
            await client.close()

    assert profile_route.call_count == 1
    assert cards_route.call_count == 1
    assert [candidate.artwork_id for candidate in candidates] == [103, 102]
    assert candidates[1].page_count == 3
    assert candidates[1].x_restrict == 1
    assert candidates[1].is_ai is True
    assert next_page == 1


@pytest.mark.asyncio
async def test_list_user_artwork_ids_combines_illustrations_and_manga() -> None:
    with respx.mock(assert_all_called=True) as router:
        router.get("https://www.pixiv.net/ajax/user/42/profile/all").mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "illusts": {"103": None, "101": None},
                        "manga": {"102": None, "0": None},
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            artwork_ids = await client.list_user_artwork_ids(42, None)
        finally:
            await client.close()

    assert artwork_ids == [103, 102, 101]


@pytest.mark.asyncio
async def test_list_followed_users_combines_public_and_private_follows() -> None:
    common_params = {
        "offset": 0,
        "limit": 100,
        "tag": "",
        "acceptingRequests": 0,
        "lang": "zh",
    }
    with respx.mock(assert_all_called=True) as router:
        router.get(
            "https://www.pixiv.net/ajax/user/42/following",
            params={**common_params, "rest": "show"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "total": 2,
                        "users": [
                            {
                                "userId": "101",
                                "userName": "公开作者",
                                "profileImageUrl": "https://i.pximg.net/101.jpg",
                            },
                            {"userId": "102", "userName": "重复作者"},
                        ],
                    },
                },
            )
        )
        router.get(
            "https://www.pixiv.net/ajax/user/42/following",
            params={**common_params, "rest": "hide"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "total": 2,
                        "users": [
                            {"userId": "102", "userName": "重复作者"},
                            {"userId": "103", "userName": "非公开作者"},
                        ],
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            users = await client.list_followed_users("PHPSESSID=42_secret")
        finally:
            await client.close()

    assert [user.user_id for user in users] == [101, 102, 103]
    assert users[0].avatar_url == "https://i.pximg.net/101.jpg"


@pytest.mark.asyncio
async def test_list_followed_users_requires_phpsessid() -> None:
    client = PixivClient(proxy_url=None, request_interval_ms=0)
    try:
        with pytest.raises(UpstreamError, match="PHPSESSID"):
            await client.list_followed_users("foo=bar")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_list_bookmark_folders_keeps_public_and_private_tags_separate() -> None:
    common_params = {"tag": "", "offset": 0, "limit": 1, "lang": "zh"}
    with respx.mock(assert_all_called=True) as router:
        router.get(
            "https://www.pixiv.net/ajax/user/42/illusts/bookmark/tags",
            params={"lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "public": [
                            {"tag": "未分類", "cnt": 1},
                            {"tag": "风景", "cnt": 2},
                        ],
                        "private": [{"tag": "私藏", "cnt": 2}],
                    },
                },
            )
        )
        router.get(
            "https://www.pixiv.net/ajax/user/42/illusts/bookmarks",
            params={**common_params, "rest": "show"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "total": 3,
                        "works": [],
                    },
                },
            )
        )
        router.get(
            "https://www.pixiv.net/ajax/user/42/illusts/bookmarks",
            params={**common_params, "rest": "hide"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "total": 2,
                        "works": [],
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            folders = await client.list_bookmark_folders("PHPSESSID=42_secret")
        finally:
            await client.close()

    assert [folder.reference.visibility for folder in folders] == [
        BookmarkVisibility.PUBLIC,
        BookmarkVisibility.PUBLIC,
        BookmarkVisibility.PUBLIC,
        BookmarkVisibility.PRIVATE,
        BookmarkVisibility.PRIVATE,
        BookmarkVisibility.PRIVATE,
    ]
    assert [(folder.kind, folder.name, folder.item_count) for folder in folders] == [
        (BookmarkFolderKind.ALL, "全部收藏", 3),
        (BookmarkFolderKind.UNCATEGORIZED, "未分类", 1),
        (BookmarkFolderKind.TAG, "风景", 2),
        (BookmarkFolderKind.ALL, "全部收藏", 2),
        (BookmarkFolderKind.UNCATEGORIZED, "未分类", 0),
        (BookmarkFolderKind.TAG, "私藏", 2),
    ]


@pytest.mark.asyncio
async def test_discover_bookmarks_uses_visibility_tag_and_page() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(
            "https://www.pixiv.net/ajax/user/42/illusts/bookmarks",
            params={
                "tag": "风景",
                "offset": 2,
                "limit": 2,
                "rest": "hide",
                "lang": "zh",
            },
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "total": 5,
                        "works": [
                            {
                                "id": "103",
                                "title": "收藏作品",
                                "illustType": 1,
                                "pageCount": 3,
                                "xRestrict": 1,
                                "aiType": 2,
                                "userName": "作者",
                                "url": "https://i.pximg.net/103.jpg",
                            },
                            {"id": "102", "title": "另一作品", "userName": "作者"},
                        ],
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            candidates, next_page = await client.discover_bookmarks(
                BookmarkFolderReference(BookmarkVisibility.PRIVATE, "风景"),
                1,
                "PHPSESSID=42_secret",
                page_size=2,
            )
        finally:
            await client.close()

    assert route.call_count == 1
    assert [candidate.artwork_id for candidate in candidates] == [103, 102]
    assert candidates[0].page_count == 3
    assert candidates[0].is_ai is True
    assert next_page == 2


@pytest.mark.asyncio
async def test_list_bookmark_artwork_ids_pages_and_deduplicates_folders() -> None:
    common_url = "https://www.pixiv.net/ajax/user/42/illusts/bookmarks"
    with respx.mock(assert_all_called=True) as router:
        router.get(
            common_url,
            params={"tag": "风景", "offset": 0, "limit": 2, "rest": "show", "lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={"error": False, "body": {"total": 3, "works": [{"id": "3"}, {"id": "2"}]}},
            )
        )
        router.get(
            common_url,
            params={"tag": "风景", "offset": 2, "limit": 2, "rest": "show", "lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={"error": False, "body": {"total": 3, "works": [{"id": "1"}]}},
            )
        )
        router.get(
            common_url,
            params={"tag": "私藏", "offset": 0, "limit": 2, "rest": "hide", "lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={"error": False, "body": {"total": 2, "works": [{"id": "2"}, {"id": "4"}]}},
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            artwork_ids = await client.list_bookmark_artwork_ids(
                [
                    BookmarkFolderReference(BookmarkVisibility.PUBLIC, "风景"),
                    BookmarkFolderReference(BookmarkVisibility.PRIVATE, "私藏"),
                ],
                "PHPSESSID=42_secret",
                page_size=2,
            )
        finally:
            await client.close()

    assert artwork_ids == [3, 2, 1, 4]


@pytest.mark.asyncio
async def test_bookmark_operations_require_phpsessid() -> None:
    client = PixivClient(proxy_url=None, request_interval_ms=0)
    try:
        with pytest.raises(UpstreamError, match="PHPSESSID"):
            await client.list_bookmark_folders("foo=bar")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_list_bookmark_artwork_ids_rejects_more_than_safety_limit(
    monkeypatch: MonkeyPatch,
) -> None:
    async def endless_page(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"total": 100_001, "works": [{"id": "1"}]}

    client = PixivClient(proxy_url=None, request_interval_ms=0)
    monkeypatch.setattr(client, "_bookmark_page", endless_page)
    try:
        with pytest.raises(UpstreamError, match="安全上限"):
            await client.list_bookmark_artwork_ids(
                [BookmarkFolderReference(BookmarkVisibility.PUBLIC, None)],
                "PHPSESSID=42_secret",
                page_size=100,
            )
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discover_artworks_fetches_only_current_page_summaries() -> None:
    with respx.mock(assert_all_called=True) as router:
        first_route = router.get("https://www.pixiv.net/ajax/illust/103").mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "illustTitle": "作品 103",
                        "illustType": 0,
                        "pageCount": 1,
                        "userName": "作者",
                        "urls": {"regular": "https://i.pximg.net/103.jpg"},
                    },
                },
            )
        )
        second_route = router.get("https://www.pixiv.net/ajax/illust/102").mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "illustTitle": "作品 102",
                        "illustType": 1,
                        "pageCount": 2,
                        "userName": "作者",
                        "urls": {"small": "https://i.pximg.net/102.jpg"},
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            candidates, next_page = await client.discover_artworks(
                ["103", "102", "101"],
                0,
                None,
                page_size=2,
            )
        finally:
            await client.close()

    assert first_route.call_count == 1
    assert second_route.call_count == 1
    assert [candidate.artwork_id for candidate in candidates] == [103, 102]
    assert candidates[0].thumbnail_url == "https://i.pximg.net/103.jpg"
    assert next_page == 1


@pytest.mark.asyncio
async def test_discover_series_uses_embedded_thumbnail_metadata() -> None:
    with respx.mock(assert_all_called=True) as router:
        series_route = router.get(
            "https://www.pixiv.net/ajax/series/7",
            params={"p": 1, "lang": "zh"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": False,
                    "body": {
                        "page": {"series": [{"workId": "302"}, {"workId": "301"}]},
                        "thumbnails": {
                            "illust": [
                                {
                                    "id": "301",
                                    "title": "第一话",
                                    "illustType": 1,
                                    "pageCount": 4,
                                    "userName": "作者",
                                    "url": "https://i.pximg.net/301.jpg",
                                },
                                {
                                    "id": "302",
                                    "title": "第二话",
                                    "illustType": 1,
                                    "pageCount": 2,
                                    "userName": "作者",
                                    "url": "https://i.pximg.net/302.jpg",
                                },
                            ]
                        },
                        "illustSeries": [{"total": 2}],
                    },
                },
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            candidates, next_page = await client.discover_series(7, 0, None)
        finally:
            await client.close()

    assert series_route.call_count == 1
    assert [candidate.artwork_id for candidate in candidates] == [302, 301]
    assert candidates[0].thumbnail_url == "https://i.pximg.net/302.jpg"
    assert next_page is None


@pytest.mark.asyncio
async def test_fetch_thumbnail_rejects_untrusted_hosts() -> None:
    client = PixivClient(proxy_url=None, request_interval_ms=0)
    try:
        with pytest.raises(UpstreamError, match="pximg"):
            await client.fetch_thumbnail("https://example.com/image.jpg", None)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_fetch_thumbnail_accepts_pximg_images() -> None:
    image = b"test-image"
    with respx.mock(assert_all_called=True) as router:
        route = router.get("https://i.pximg.net/example.jpg").mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "image/jpeg"},
                content=image,
            )
        )
        client = PixivClient(proxy_url=None, request_interval_ms=0)
        try:
            content, media_type = await client.fetch_thumbnail(
                "https://i.pximg.net/example.jpg",
                None,
            )
        finally:
            await client.close()

    assert route.call_count == 1
    assert content == image
    assert media_type == "image/jpeg"
