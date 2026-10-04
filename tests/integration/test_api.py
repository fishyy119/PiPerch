from __future__ import annotations

import json
from dataclasses import replace
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from piperch.domain import (
    ArtworkType,
    BookmarkFolder,
    BookmarkFolderKind,
    BookmarkFolderReference,
    BookmarkVisibility,
    DiscoveryCandidate,
    FollowedUser,
    MediaRecord,
    RemoteArtwork,
    TagRecord,
)
from piperch.services.storage import StorageMigrationSelection

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pytest import MonkeyPatch
    from tests.support import ApiTestClient

    from piperch.container import AppContainer


def test_user_artwork_ids_returns_all_ids_without_loading_pages(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    client, container = app_client

    async def list_ids(user_id: int, cookie: str | None) -> list[int]:
        assert user_id == 42
        assert cookie is None
        return [103, 102, 101]

    def find_existing_ids(artwork_ids: Sequence[int]) -> set[int]:
        assert artwork_ids == [103, 102, 101]
        return {102}

    monkeypatch.setattr(container.pixiv, "list_user_artwork_ids", list_ids)
    monkeypatch.setattr(container.artworks, "find_existing_ids", find_existing_ids)

    response = client.get("/api/discovery/users/42/selectable-artwork-ids")

    assert response.status_code == 200
    assert response.json() == {"artworkIds": [103, 101]}


def test_followed_users_returns_safe_author_fields(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    client, container = app_client

    async def list_followed_users(cookie: str | None) -> list[FollowedUser]:
        assert cookie is None
        return [FollowedUser(101, "测试作者", "https://i.pximg.net/avatar.jpg")]

    monkeypatch.setattr(container.pixiv, "list_followed_users", list_followed_users)

    response = client.get("/api/authors/followed")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "userId": 101,
                "name": "测试作者",
                "avatarUrl": "/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2Favatar.jpg",
            }
        ]
    }


def test_bookmark_folders_keep_visibility_and_special_kind(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    client, container = app_client

    async def list_bookmark_folders(cookie: str | None) -> list[BookmarkFolder]:
        assert cookie is None
        return [
            BookmarkFolder(
                BookmarkFolderReference(BookmarkVisibility.PUBLIC, None),
                BookmarkFolderKind.ALL,
                "全部收藏",
                12,
            ),
            BookmarkFolder(
                BookmarkFolderReference(BookmarkVisibility.PRIVATE, "私藏"),
                BookmarkFolderKind.TAG,
                "私藏",
                3,
            ),
        ]

    monkeypatch.setattr(container.pixiv, "list_bookmark_folders", list_bookmark_folders)

    response = client.get("/api/discovery/bookmark-folders")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "visibility": "public",
                "tag": None,
                "kind": "all",
                "name": "全部收藏",
                "itemCount": 12,
            },
            {
                "visibility": "private",
                "tag": "私藏",
                "kind": "tag",
                "name": "私藏",
                "itemCount": 3,
            },
        ]
    }


def test_bookmark_discovery_marks_existing_artworks(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    client, container = app_client

    async def discover_bookmarks(
        folder: BookmarkFolderReference,
        page: int,
        cookie: str | None,
    ) -> tuple[list[DiscoveryCandidate], int | None]:
        assert folder == BookmarkFolderReference(BookmarkVisibility.PRIVATE, "私藏")
        assert page == 0
        assert cookie is None
        return (
            [
                DiscoveryCandidate(101, "已有作品", "作者", ArtworkType.ILLUST, 1, 0, False, None),
                DiscoveryCandidate(102, "收藏作品", "作者", ArtworkType.MANGA, 2, 0, False, None),
            ],
            1,
        )

    def find_existing_ids(artwork_ids: Sequence[int]) -> set[int]:
        assert artwork_ids == [101, 102]
        return {101}

    monkeypatch.setattr(container.pixiv, "discover_bookmarks", discover_bookmarks)
    monkeypatch.setattr(container.artworks, "find_existing_ids", find_existing_ids)

    response = client.post(
        "/api/discovery",
        json={
            "sourceType": "bookmark",
            "folder": {"visibility": "private", "tag": "私藏"},
            "page": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 0
    assert payload["nextPage"] == 1
    assert [item["inLibrary"] for item in payload["items"]] == [True, False]


def test_selectable_bookmark_artwork_ids_deduplicates_request_and_excludes_existing(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    client, container = app_client

    async def list_bookmark_artwork_ids(
        folders: Sequence[BookmarkFolderReference],
        cookie: str | None,
    ) -> list[int]:
        assert folders == [
            BookmarkFolderReference(BookmarkVisibility.PUBLIC, "风景"),
            BookmarkFolderReference(BookmarkVisibility.PRIVATE, None),
        ]
        assert cookie is None
        return [103, 102, 101]

    def find_existing_bookmark_ids(artwork_ids: Sequence[int]) -> set[int]:
        assert artwork_ids == [103, 102, 101]
        return {102}

    monkeypatch.setattr(container.pixiv, "list_bookmark_artwork_ids", list_bookmark_artwork_ids)
    monkeypatch.setattr(container.artworks, "find_existing_ids", find_existing_bookmark_ids)

    response = client.post(
        "/api/discovery/bookmarks/selectable-artwork-ids",
        json={
            "folders": [
                {"visibility": "public", "tag": "风景"},
                {"visibility": "public", "tag": "风景"},
                {"visibility": "private", "tag": None},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"artworkIds": [103, 101]}


def test_discovery_marks_artwork_already_in_library(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    client, container = app_client
    local_artwork = RemoteArtwork(
        artwork_id=101,
        artwork_type=ArtworkType.ILLUST,
        title="本地作品",
        description="",
        author_id=201,
        author_name="作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=1000,
        height=1000,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/101.jpg",),
        thumbnail_url=None,
    )
    container.download_commits.commit(
        local_artwork,
        [MediaRecord("page", "201/101/101_p0.jpg", "image/jpeg", 10, 0)],
    )

    async def discover_artworks(
        inputs: list[str],
        page: int,
        cookie: str | None,
    ) -> tuple[list[DiscoveryCandidate], None]:
        assert inputs == ["101", "102"]
        assert page == 0
        assert cookie is None
        return (
            [
                DiscoveryCandidate(101, "本地作品", "作者", ArtworkType.ILLUST, 1, 0, False, None),
                DiscoveryCandidate(
                    102,
                    "远端作品",
                    "作者",
                    ArtworkType.ILLUST,
                    2,
                    0,
                    False,
                    "https://i.pximg.net/102.jpg",
                ),
            ],
            None,
        )

    monkeypatch.setattr(container.pixiv, "discover_artworks", discover_artworks)

    response = client.post(
        "/api/discovery",
        json={"sourceType": "artwork", "inputs": ["101", "102"], "page": 0},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["inLibrary"] for item in items] == [True, False]
    assert items[1]["thumbnailUrl"] == "/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2F102.jpg"


def test_health_and_settings_return_cookie(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    assert client.get("/api/health").json() == {
        "status": "ok",
        "database": "ok",
        "instanceId": container.instance_id,
    }

    cookie = "PHPSESSID=123_secret-value"
    response = client.patch(
        "/api/settings",
        json={"pixivCookie": cookie},
    )
    assert response.status_code == 200
    assert response.json()["pixivCookie"] == cookie
    persisted = json.loads(container.paths.settings.read_text(encoding="utf-8"))
    assert persisted["pixiv_cookie"] == cookie

    settings = client.get("/api/settings")
    assert settings.status_code == 200
    assert settings.json()["pixivCookie"] == cookie

    cleared = client.patch(
        "/api/settings",
        json={"pixivCookie": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["pixivCookie"] is None
    persisted = json.loads(container.paths.settings.read_text(encoding="utf-8"))
    assert persisted["pixiv_cookie"] is None
    assert client.get("/api/settings").json()["pixivCookie"] is None


def test_settings_patch_and_proxy_redaction(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    original_library = container.settings.get().library_root
    response = client.patch(
        "/api/settings",
        json={"proxyUrl": "http://user:password@127.0.0.1:7890"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proxyUrl"] == "http://user:***@127.0.0.1:7890"
    persisted = json.loads(container.paths.settings.read_text(encoding="utf-8"))
    assert persisted["proxy_url"] == "http://user:password@127.0.0.1:7890"

    library_response = client.patch("/api/settings", json={"libraryRoot": "C:\\other-library"})
    assert library_response.status_code == 422
    assert container.settings.get().library_root == original_library

    repeated = client.patch(
        "/api/settings",
        json={"proxyUrl": payload["proxyUrl"]},
    )
    assert repeated.status_code == 200
    assert container.settings.get().proxy_url == "http://user:password@127.0.0.1:7890"


def test_library_migration_endpoint_reports_cancelled_and_started(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, container = app_client
    monkeypatch.setattr(container.storage, "prepare_interactive", lambda: None)

    cancelled = client.post("/api/settings/library-root/migrate")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.setattr(
        container.storage,
        "prepare_interactive",
        lambda: StorageMigrationSelection(target),
    )
    migrated: list[Path] = []

    async def migrate(path: Path) -> None:
        migrated.append(path)

    monkeypatch.setattr(container.storage, "migrate", migrate)

    started = client.post("/api/settings/library-root/migrate")

    assert started.status_code == 202
    payload = started.json()
    assert payload["status"] == "started"
    assert payload["targetPath"] == str(target)
    assert payload["instanceId"] == container.instance_id
    assert migrated == [target]


def test_settings_patch_updates_only_requested_fields(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    current = container.settings.get()

    concurrency = client.patch("/api/settings", json={"downloadConcurrency": 6})
    assert concurrency.status_code == 200
    assert concurrency.json()["downloadConcurrency"] == 6
    assert concurrency.json()["requestIntervalMs"] == current.request_interval_ms

    disabled = client.patch("/api/settings", json={"webpEnabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["downloadConcurrency"] == 6
    assert disabled.json()["webpEnabled"] is False

    persisted = json.loads(container.paths.settings.read_text(encoding="utf-8"))
    assert persisted["download_concurrency"] == 6
    assert persisted["webp_enabled"] is False


def test_settings_patch_rejects_empty_or_invalid_changes(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, _ = app_client

    assert client.patch("/api/settings", json={}).status_code == 422
    assert client.patch("/api/settings", json={"downloadConcurrency": 9}).status_code == 422


def test_settings_rejects_invalid_proxy_without_persisting(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    current = container.settings.get()
    persisted = container.paths.settings.read_text(encoding="utf-8")

    response = client.patch(
        "/api/settings",
        json={"proxyUrl": "http://127.0.0.1:invalid"},
    )

    assert response.status_code == 422
    assert container.paths.settings.read_text(encoding="utf-8") == persisted
    assert container.settings.get() == current


def test_unknown_api_path_returns_json_error(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, _ = app_client
    response = client.get("/api/not-found")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_validation_error_uses_stable_envelope(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, _ = app_client
    response = client.post("/api/settings/pixiv-cookie/validate", json={"value": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_artwork_page_thumbnail_is_created_for_existing_media(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    artwork = RemoteArtwork(
        artwork_id=101,
        artwork_type=ArtworkType.ILLUST,
        title="已有作品",
        description="",
        author_id=201,
        author_name="测试作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=640,
        height=320,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/101.jpg",),
        thumbnail_url=None,
    )
    source = container.settings.get().library_root / "201" / "101" / "101_p0.jpg"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (640, 320), (30, 120, 210)).save(source, "JPEG")
    container.download_commits.commit(
        artwork,
        [MediaRecord("page", "201/101/101_p0.jpg", "image/jpeg", source.stat().st_size, 0)],
    )

    response = client.get("/api/artworks/101/pages/0/thumbnail")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    with Image.open(BytesIO(response.content)) as thumbnail:
        assert thumbnail.format == "WEBP"
        assert thumbnail.size == (256, 128)


def test_download_job_list_uses_summary_and_detail_includes_items(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    job_id = container.downloads.create_job([101], "接口契约测试")
    claimed = container.downloads.claim_next()
    assert claimed is not None

    summary = client.get("/api/download-jobs?size=100")
    detail = client.get(f"/api/download-jobs/{job_id}")

    assert summary.status_code == 200
    assert summary.json()["items"][0]["jobId"] == job_id
    assert "items" not in summary.json()["items"][0]
    assert "cancelRequested" not in summary.json()["items"][0]
    assert "progress" not in summary.json()["items"][0]
    assert summary.json()["items"][0]["counts"]["running"] == 1
    assert detail.status_code == 200
    assert [item["artworkId"] for item in detail.json()["items"]] == [101]


def test_gallery_accepts_camel_case_filter_parameters(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    first = RemoteArtwork(
        artwork_id=101,
        artwork_type=ArtworkType.MANGA,
        title="目标作品",
        description="",
        author_id=201,
        author_name="目标作者",
        author_account=None,
        author_avatar_url=None,
        series_id=301,
        series_title="目标系列",
        page_count=1,
        width=1000,
        height=1200,
        x_restrict=1,
        is_ai=True,
        published_at=None,
        original_urls=("https://i.pximg.net/target.jpg",),
        thumbnail_url=None,
        tags=(TagRecord("目标标签"),),
    )
    second = RemoteArtwork(
        artwork_id=102,
        artwork_type=ArtworkType.ILLUST,
        title="其他作品",
        description="",
        author_id=202,
        author_name="其他作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=1000,
        height=1200,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/other.jpg",),
        thumbnail_url=None,
        tags=(TagRecord("其他标签"),),
    )
    container.download_commits.commit(
        first,
        [MediaRecord("page", "201/101/101_p0.jpg", "image/jpeg", 10, 0)],
    )
    container.download_commits.commit(
        second,
        [MediaRecord("page", "202/102/102_p0.jpg", "image/jpeg", 10, 0)],
    )
    target_tag_id = next(tag_id for tag_id, tag, _ in container.artworks.list_tags("", 50) if tag.name == "目标标签")

    response = client.get(
        f"/api/artworks?tagId={target_tag_id}&authorId=201&seriesId=301&artworkType=manga&rating=r18&ai=yes"
    )
    tags_response = client.get(f"/api/tags?search=其他&limit=1&includeId={target_tag_id}")
    authors_response = client.get("/api/authors?search=其他&limit=1&includeId=201")

    assert response.status_code == 200
    payload = response.json()
    assert payload["totalElements"] == 1
    assert [item["artworkId"] for item in payload["items"]] == [101]
    assert tags_response.status_code == 200
    assert [item["name"] for item in tags_response.json()] == ["目标标签", "其他标签"]
    assert authors_response.status_code == 200
    assert [item["name"] for item in authors_response.json()] == ["目标作者", "其他作者"]


def test_local_groups_can_organize_non_favorite_artworks(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    artwork = RemoteArtwork(
        artwork_id=701,
        artwork_type=ArtworkType.ILLUST,
        title="非收藏作品",
        description="",
        author_id=801,
        author_name="测试作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=1000,
        height=1200,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/artwork.jpg",),
        thumbnail_url=None,
    )
    media = [MediaRecord("page", "801/701/701_p0.jpg", "image/jpeg", 10, 0)]
    container.download_commits.commit(artwork, media)

    local_group = client.post("/api/groups", json={"name": "本地分组"})
    assert local_group.status_code == 200
    local_group_id = local_group.json()["groupId"]

    grouped = client.put(
        "/api/artworks/701/groups",
        json={"groupIds": [local_group_id]},
    )
    assert grouped.status_code == 200
    assert grouped.json() == {"artworkId": 701, "groupIds": [local_group_id]}

    filtered = client.get(
        "/api/artworks",
        params=[("favorite", "no"), ("groupId", local_group_id)],
    )
    assert filtered.status_code == 200
    assert [item["artworkId"] for item in filtered.json()["items"]] == [701]


def test_manual_favorite_sync_previews_before_updating_local_state(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    client, container = app_client
    artwork = RemoteArtwork(
        artwork_id=901,
        artwork_type=ArtworkType.ILLUST,
        title="本地收藏同步作品",
        description="",
        author_id=902,
        author_name="同步作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=1000,
        height=1200,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/901.jpg",),
        thumbnail_url=None,
    )
    for artwork_id in (901, 902, 903):
        current = replace(
            artwork,
            artwork_id=artwork_id,
            title=f"同步作品 {artwork_id}",
            original_urls=(f"https://i.pximg.net/{artwork_id}.jpg",),
        )
        container.download_commits.commit(
            current,
            [MediaRecord("page", f"902/{artwork_id}/{artwork_id}_p0.jpg", "image/jpeg", 10, 0)],
        )
    container.favorites.replace_state(901, is_favorite=True)
    container.favorites.replace_state(902, is_favorite=True)

    async def list_bookmark_artwork_ids(
        folders: Sequence[BookmarkFolderReference],
        cookie: str | None,
    ) -> list[int]:
        assert folders == [
            BookmarkFolderReference(BookmarkVisibility.PUBLIC, None),
            BookmarkFolderReference(BookmarkVisibility.PRIVATE, None),
        ]
        assert cookie is None
        return [902, 903, 999]

    monkeypatch.setattr(container.pixiv, "list_bookmark_artwork_ids", list_bookmark_artwork_ids)

    preview = client.post("/api/favorite-sync-plans")

    assert preview.status_code == 200
    preview_payload = preview.json()
    plan_id = preview_payload.pop("planId")
    assert isinstance(plan_id, str)
    assert preview_payload == {
        "pixivFavoriteCount": 3,
        "localArtworkCount": 3,
        "localFavoriteCount": 2,
        "matchedFavoriteCount": 2,
        "unavailableLocallyCount": 1,
        "addCount": 1,
        "removeCount": 1,
    }
    assert container.favorites.get_state(901).is_favorite is True
    assert container.favorites.get_state(902).is_favorite is True
    assert container.favorites.get_state(903).is_favorite is False

    applied = client.post(f"/api/favorite-sync-plans/{plan_id}/apply")

    assert applied.status_code == 200
    assert applied.json() == {"added": 1, "removed": 1}
    assert container.favorites.get_state(901).is_favorite is False
    assert container.favorites.get_state(902).is_favorite is True
    assert container.favorites.get_state(903).is_favorite is True
    assert client.post(f"/api/favorite-sync-plans/{plan_id}/apply").status_code == 409
