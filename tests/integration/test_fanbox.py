from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import httpx
import pytest
import respx
from PIL import Image

from piperch.domain.downloads import ItemState
from piperch.domain.sources import ArtworkSource
from piperch.fanbox import FanboxClient
from piperch.services.downloads import ArtworkDownloadService, DownloadCancellation

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from tests.support import ApiTestClient

    from piperch.application.container import AppContainer


@pytest.mark.asyncio
async def test_fanbox_download_stores_only_image_attachments_without_remote_bookmarks(
    app_client: tuple[ApiTestClient, AppContainer],
    monkeypatch: MonkeyPatch,
) -> None:
    _, container = app_client
    images: list[bytes] = []
    for color in ("blue", "red"):
        image = BytesIO()
        Image.new("RGB", (8, 8), color).save(image, "PNG")
        images.append(image.getvalue())
    files = [
        {"name": "first.png", "path": f"/aa/aa/{'a' * 64}.png"},
        {"name": "second.png", "path": f"/bb/bb/{'b' * 64}.png", "node": 2},
    ]
    archive = {"name": "archive.zip", "path": f"/cc/cc/{'c' * 64}.zip", "node": 2}
    cover = {"name": "cover.png", "path": f"/dd/dd/{'d' * 64}.png", "node": 2}
    post = {
        "id": "701",
        "user": "100",
        "service": "fanbox",
        "title": "Images",
        "content": "<p>Body</p>",
        "published": "2026-11-07T00:00:00",
        "file": cover,
        "attachments": [files[0], archive, files[0], files[1]],
    }
    bookmark_calls: list[int] = []

    async def record_bookmark(artwork_id: int, _favorite: bool, _cookie: str | None) -> None:
        bookmark_calls.append(artwork_id)

    monkeypatch.setattr(container.pixiv, "sync_bookmark_state", record_bookmark)
    container.settings.patch(auto_bookmark_on_download=True, webp_enabled=False)
    with respx.mock(assert_all_called=False) as upstream:
        upstream.get("https://pawchive.pw/api/v1/fanbox/user/100/profile").mock(
            return_value=httpx.Response(200, json={"id": "100", "service": "fanbox", "name": "Artist"})
        )
        upstream.get("https://pawchive.pw/api/v1/fanbox/user/100/post/701").mock(
            return_value=httpx.Response(200, json=post)
        )
        for url, content in zip(
            (f"https://file.pawchive.pw/data{files[0]['path']}", f"https://n2.pawchive.pw/data{files[1]['path']}"),
            images,
            strict=True,
        ):
            upstream.get(url).mock(
                return_value=httpx.Response(200, content=content, headers={"content-type": "image/png"})
            )

        service = ArtworkDownloadService(
            container.paths,
            container.settings,
            container.artworks,
            container.pixiv,
            container.download_commits,
            container.favorites,
            fanbox=container.fanbox,
        )
        state = await service.download_artwork(
            701, "fanbox-test", DownloadCancellation(), source=ArtworkSource.FANBOX, author_id=100
        )
        assert state is ItemState.SUCCEEDED

    local_id = container.artworks.find_local_ids([701], ArtworkSource.FANBOX)[701]
    media = container.artworks.list_media(local_id)
    assert len(media) == 2
    for item, expected in zip(media, images, strict=True):
        assert item.relative_path.startswith("fanbox/100/701/")
        assert (container.settings.get().library_root / item.relative_path).read_bytes() == expected
    assert bookmark_calls == []


@pytest.mark.asyncio
async def test_fanbox_pagination_preserves_empty_website_pages_after_image_filtering() -> None:
    client = FanboxClient(proxy_url=None, request_interval_ms=0)
    image = {"name": "image.png", "path": f"/aa/aa/{'a' * 64}.png", "node": 2}
    posts: list[dict[str, object]] = [
        {"id": str(index), "user": "100", "service": "fanbox", "file": image, "attachments": []}
        for index in range(1, 102)
    ]
    posts[50]["attachments"] = [image]
    try:
        with respx.mock(assert_all_called=False) as upstream:
            upstream.get("https://pawchive.pw/api/v1/fanbox/user/100/profile").mock(
                return_value=httpx.Response(200, json={"id": "100", "service": "fanbox", "name": "Artist"})
            )
            for page in range(3):
                upstream.get("https://pawchive.pw/api/v1/fanbox/user/100", params={"o": page * 50}).mock(
                    return_value=httpx.Response(200, json=posts[page * 50 : (page + 1) * 50])
                )
                upstream.get("https://pawchive.pw/fanbox/user/100", params={"o": page * 50}).mock(
                    return_value=httpx.Response(
                        200, text=f"<small>Showing {page * 50 + 1} - {min((page + 1) * 50, 101)} of 101</small>"
                    )
                )

            first = await client.discover_user(100, 0)
            assert first.candidates == []
            assert (first.next_page, first.total_pages) == (1, 3)
            middle = await client.discover_user(100, 1)
            assert [candidate.artwork_id for candidate in middle.candidates] == [51]
            assert (middle.next_page, middle.total_pages) == (2, 3)
            last = await client.discover_user(100, 2)
            assert last.candidates == []
            assert (last.next_page, last.total_pages) == (None, 3)
    finally:
        await client.close()
