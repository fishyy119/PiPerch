from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from anyio import to_thread
from PIL import Image

from piperch.database import Database, run_migrations
from piperch.domain.artworks import ArtworkType, MediaRecord, RemoteArtwork
from piperch.domain.downloads import ItemState
from piperch.domain.favorites import FavoriteState
from piperch.errors import UpstreamError
from piperch.paths import AppPaths
from piperch.repositories import ArtworkGroupRepository, ArtworkRepository, FavoriteRepository
from piperch.services.downloads import (
    ArtworkDownloadCommitService,
    ArtworkDownloadService,
    DownloadCancellation,
    DownloadCancelledError,
)
from piperch.services.events import AppEventBroker
from piperch.services.library_commits import LibraryCommitCoordinator
from piperch.services.tag_search import TagSearchIndex
from piperch.services.thumbnails import ArtworkThumbnailCache
from piperch.settings import SettingsManager
from piperch.settings.models import AppSettings

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pytest import MonkeyPatch

    from piperch.pixiv import PixivClient


class StubSettings:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def get(self) -> AppSettings:
        return self._settings


class StubArtworkRepository:
    def is_complete(self, _artwork_id: int, _library_root: Path) -> bool:
        return False

    def find_existing_ids(self, _artwork_ids: Sequence[int]) -> set[int]:
        return set()

    def list_media(self, _artwork_id: int) -> tuple[MediaRecord, ...]:
        return ()


class StubArtworkDownloadCommitService:
    def __init__(self) -> None:
        self.saved_media: tuple[MediaRecord, ...] | None = None

    def commit(self, _artwork: RemoteArtwork, media: Sequence[MediaRecord]) -> None:
        self.saved_media = tuple(media)


class StubFavoriteRepository:
    def __init__(self) -> None:
        self.is_favorite = False

    def replace_state(self, artwork_id: int, *, is_favorite: bool) -> FavoriteState:
        self.is_favorite = is_favorite
        return FavoriteState(artwork_id, is_favorite)


class StubPixivClient:
    def __init__(
        self,
        artwork: RemoteArtwork,
        on_download: Callable[[], None] | None = None,
    ) -> None:
        self._artwork = artwork
        self._on_download = on_download
        self.active_downloads = 0
        self.maximum_active_downloads = 0
        self.bookmarked_ids: set[int] = set()

    async def get_artwork(self, artwork_id: int, _cookie: str | None) -> RemoteArtwork:
        assert artwork_id == self._artwork.artwork_id
        return self._artwork

    async def sync_bookmark_state(self, artwork_id: int, is_favorite: bool, _cookie: str | None) -> None:
        if is_favorite:
            self.bookmarked_ids.add(artwork_id)
        else:
            self.bookmarked_ids.discard(artwork_id)

    async def download(self, _url: str, target: Path) -> tuple[str, int]:
        self.active_downloads += 1
        self.maximum_active_downloads = max(self.maximum_active_downloads, self.active_downloads)
        try:
            Image.new("RGBA", (8, 8), (30, 120, 210, 128)).save(target, "PNG")
            size = await to_thread.run_sync(lambda: target.stat().st_size)
            if self._on_download is not None:
                self._on_download()
            return "image/png", size
        finally:
            self.active_downloads -= 1


class FailingThumbnailCache(ArtworkThumbnailCache):
    def create_cover_thumbnail(self, artwork_id: int, source: Path) -> Path:
        raise OSError("thumbnail failed")


@pytest.mark.asyncio
@pytest.mark.parametrize(("webp_enabled", "expected_suffix"), [(True, ".webp"), (False, ".png")])
async def test_download_writes_configured_image_format(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    webp_enabled: bool,
    expected_suffix: str,
) -> None:
    paths = AppPaths.from_data_dir(tmp_path / "data")
    paths.ensure_directories()
    settings = AppSettings(
        pixiv_cookie=None,
        proxy_url=None,
        library_root=paths.default_library,
        download_concurrency=1,
        request_interval_ms=0,
        auto_bookmark_on_download=False,
        webp_enabled=webp_enabled,
        webp_quality=67,
    )
    artwork = RemoteArtwork(
        artwork_id=123,
        artwork_type=ArtworkType.ILLUST,
        title="测试作品",
        description="",
        author_id=456,
        author_name="测试作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=3,
        width=8,
        height=8,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=(
            "https://i.pximg.net/123_p0.png",
            "https://i.pximg.net/123_p1.png",
            "https://i.pximg.net/123_p2.png",
        ),
        thumbnail_url=None,
    )
    repository = StubArtworkRepository()
    commits = StubArtworkDownloadCommitService()
    pixiv = StubPixivClient(artwork)
    qualities: list[int] = []
    transcode = ArtworkDownloadService._transcode_to_webp  # pyright: ignore[reportPrivateUsage]

    def capture_quality(source: Path, quality: int) -> tuple[Path, int]:
        qualities.append(quality)
        return transcode(source, quality)

    monkeypatch.setattr(ArtworkDownloadService, "_transcode_to_webp", capture_quality)
    service = ArtworkDownloadService(
        paths,
        cast("SettingsManager", StubSettings(settings)),
        cast("ArtworkRepository", repository),
        cast("PixivClient", pixiv),
        cast("ArtworkDownloadCommitService", commits),
        cast("FavoriteRepository", StubFavoriteRepository()),
    )

    result = await service.download_artwork(123, "job-id", DownloadCancellation())

    assert result is ItemState.SUCCEEDED
    assert pixiv.maximum_active_downloads == 1
    assert qualities == ([67, 67, 67] if webp_enabled else [])
    assert commits.saved_media is not None
    media = commits.saved_media[0]
    assert Path(media.relative_path).suffix == expected_suffix
    assert media.mime_type == ("image/webp" if webp_enabled else "image/png")
    saved = settings.library_root / media.relative_path
    assert saved.is_file()
    with Image.open(saved) as image:
        assert image.format == ("WEBP" if webp_enabled else "PNG")
        assert "A" in image.getbands()
        pixel = image.getpixel((0, 0))
        assert isinstance(pixel, tuple) and len(pixel) == 4
        assert pixel[3] == 128
    assert (paths.thumbnails / "123.webp").is_file()
    page_thumbnails = sorted((paths.thumbnails / "pages" / "123").glob("*.webp"))
    assert [path.name for path in page_thumbnails] == ["0.webp", "1.webp", "2.webp"]


@pytest.mark.asyncio
async def test_thumbnail_failure_keeps_committed_artwork_files(tmp_path: Path) -> None:
    paths = AppPaths.from_data_dir(tmp_path / "data")
    paths.ensure_directories()
    settings = AppSettings(
        pixiv_cookie=None,
        proxy_url=None,
        library_root=paths.default_library,
        download_concurrency=1,
        request_interval_ms=0,
        auto_bookmark_on_download=False,
        webp_enabled=False,
        webp_quality=75,
    )
    artwork = RemoteArtwork(
        artwork_id=123,
        artwork_type=ArtworkType.ILLUST,
        title="测试作品",
        description="",
        author_id=456,
        author_name="测试作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=8,
        height=8,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/123_p0.png",),
        thumbnail_url=None,
    )
    repository = StubArtworkRepository()
    commits = StubArtworkDownloadCommitService()
    service = ArtworkDownloadService(
        paths,
        cast("SettingsManager", StubSettings(settings)),
        cast("ArtworkRepository", repository),
        cast("PixivClient", StubPixivClient(artwork)),
        cast("ArtworkDownloadCommitService", commits),
        cast("FavoriteRepository", StubFavoriteRepository()),
        FailingThumbnailCache(paths),
    )

    result = await service.download_artwork(123, "job-id", DownloadCancellation())

    assert result is ItemState.SUCCEEDED
    assert commits.saved_media is not None
    assert (settings.library_root / commits.saved_media[0].relative_path).is_file()


@pytest.mark.asyncio
async def test_cancellation_before_commit_discards_staged_media(tmp_path: Path) -> None:
    paths = AppPaths.from_data_dir(tmp_path / "data")
    paths.ensure_directories()
    settings = AppSettings(
        pixiv_cookie=None,
        proxy_url=None,
        library_root=paths.default_library,
        download_concurrency=1,
        request_interval_ms=0,
        auto_bookmark_on_download=True,
        webp_enabled=False,
        webp_quality=75,
    )
    artwork = RemoteArtwork(
        artwork_id=123,
        artwork_type=ArtworkType.ILLUST,
        title="测试作品",
        description="",
        author_id=456,
        author_name="测试作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=8,
        height=8,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/123_p0.png",),
        thumbnail_url=None,
    )
    repository = StubArtworkRepository()
    commits = StubArtworkDownloadCommitService()
    cancellation = DownloadCancellation()

    def request_cancel() -> None:
        cancellation.request()

    pixiv = StubPixivClient(artwork, request_cancel)
    favorites = StubFavoriteRepository()
    service = ArtworkDownloadService(
        paths,
        cast("SettingsManager", StubSettings(settings)),
        cast("ArtworkRepository", repository),
        cast("PixivClient", pixiv),
        cast("ArtworkDownloadCommitService", commits),
        cast("FavoriteRepository", favorites),
    )

    with pytest.raises(DownloadCancelledError):
        await service.download_artwork(123, "job-id", cancellation)

    assert commits.saved_media is None
    assert not (settings.library_root / "456" / "123").exists()
    assert pixiv.bookmarked_ids == set()
    assert favorites.is_favorite is False


@pytest.mark.asyncio
async def test_bookmark_failure_keeps_downloaded_artwork_without_marking_local_favorite(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    paths = AppPaths.from_data_dir(tmp_path / "data")
    paths.ensure_directories()
    run_migrations(paths)
    database = Database(paths.database)
    settings = SettingsManager(paths.settings, paths.default_library)
    settings.initialize()
    settings.patch(pixiv_cookie="PHPSESSID=123_test", webp_enabled=False)
    artwork = RemoteArtwork(
        artwork_id=123,
        artwork_type=ArtworkType.ILLUST,
        title="测试作品",
        description="",
        author_id=456,
        author_name="测试作者",
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=8,
        height=8,
        x_restrict=0,
        is_ai=False,
        published_at=None,
        original_urls=("https://i.pximg.net/123_p0.png",),
        thumbnail_url=None,
    )
    artworks = ArtworkRepository(database)
    favorites = FavoriteRepository(database)
    commits = ArtworkDownloadCommitService(
        database,
        artworks,
        favorites,
        ArtworkGroupRepository(database),
        TagSearchIndex(database),
        library_commits=LibraryCommitCoordinator(AppEventBroker()),
    )
    pixiv = StubPixivClient(artwork)
    bookmark_failed = False

    async def fail_bookmark(_artwork_id: int, _is_favorite: bool, _cookie: str | None) -> None:
        nonlocal bookmark_failed
        bookmark_failed = True
        raise UpstreamError("pixiv_write_failed", "Pixiv 收藏更新失败。")

    monkeypatch.setattr(pixiv, "sync_bookmark_state", fail_bookmark)
    service = ArtworkDownloadService(paths, settings, artworks, cast("PixivClient", pixiv), commits, favorites)
    try:
        result = await service.download_artwork(123, "job-id", DownloadCancellation())

        assert bookmark_failed
        assert result is ItemState.SUCCEEDED
        assert artworks.is_complete(123, settings.get().library_root)
        assert favorites.get_state(123).is_favorite is False
        assert pixiv.bookmarked_ids == set()
    finally:
        database.close()
