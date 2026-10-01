from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from piperch.domain import (
    ArtworkType,
    BookmarkFolder,
    BookmarkFolderKind,
    BookmarkFolderReference,
    BookmarkVisibility,
    DiscoveryCandidate,
    DownloadProgressPhase,
    FollowedUser,
    MediaRecord,
    RemoteArtwork,
    TagRecord,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

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

    response = client.get("/api/discovery/followed-users")

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
    container.artworks.save_download(
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
    assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}

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
    tmp_path: Path,
) -> None:
    client, container = app_client
    library = tmp_path / "library"
    response = client.patch(
        "/api/settings",
        json={"proxyUrl": "http://user:password@127.0.0.1:7890"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proxyUrl"] == "http://user:***@127.0.0.1:7890"
    persisted = json.loads(container.paths.settings.read_text(encoding="utf-8"))
    assert persisted["proxy_url"] == "http://user:password@127.0.0.1:7890"

    library_response = client.patch("/api/settings", json={"libraryRoot": str(library)})
    assert library_response.status_code == 200
    assert Path(library_response.json()["libraryRoot"]) == library.resolve()
    persisted = json.loads(container.paths.settings.read_text(encoding="utf-8"))
    assert persisted["library_root"] == str(library.resolve())

    repeated = client.patch(
        "/api/settings",
        json={"proxyUrl": payload["proxyUrl"]},
    )
    assert repeated.status_code == 200
    assert container.settings.get().proxy_url == "http://user:password@127.0.0.1:7890"


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


def test_gallery_rejects_invalid_artwork_ids(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, _ = app_client

    assert client.get("/api/artworks/0").status_code == 422
    assert client.get("/api/artworks/1/pages/-1").status_code == 422
    assert client.get("/api/artworks?tagId=0").status_code == 422
    assert client.post("/api/artworks/bulk-delete", json={"artworkIds": [1, 0]}).status_code == 422


def test_download_job_list_uses_summary_and_detail_includes_items(
    app_client: tuple[ApiTestClient, AppContainer],
) -> None:
    client, container = app_client
    job_id = container.downloads.create_job([101], "接口契约测试")
    claimed = container.downloads.claim_next()
    assert claimed is not None
    _, item = claimed
    container.downloads.update_item_progress(
        item.item_id,
        DownloadProgressPhase.DOWNLOADING,
        2,
        5,
    )

    summary = client.get("/api/download-jobs?size=100")
    detail = client.get(f"/api/download-jobs/{job_id}")

    assert summary.status_code == 200
    assert summary.json()["items"][0]["jobId"] == job_id
    assert "items" not in summary.json()["items"][0]
    assert "cancelRequested" not in summary.json()["items"][0]
    assert summary.json()["items"][0]["progress"] == {
        "currentArtworkId": 101,
        "completedPages": 2,
        "totalPages": 5,
        "phase": "downloading",
    }
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
    container.artworks.save_download(
        first,
        [MediaRecord("page", "201/101/101_p0.jpg", "image/jpeg", 10, 0)],
    )
    container.artworks.save_download(
        second,
        [MediaRecord("page", "202/102/102_p0.jpg", "image/jpeg", 10, 0)],
    )
    target_tag_id = next(tag_id for tag_id, tag, _ in container.artworks.list_tags("", 50) if tag.name == "目标标签")

    response = client.get(
        f"/api/artworks?tagId={target_tag_id}&authorId=201&seriesId=301&artworkType=manga&rating=r18&ai=yes"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["totalElements"] == 1
    assert [item["artworkId"] for item in payload["items"]] == [101]
