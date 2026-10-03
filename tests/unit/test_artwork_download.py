from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from anyio import to_thread
from PIL import Image

from piperch.domain import (
    AppSettings,
    ArtworkType,
    ItemState,
    MediaRecord,
    RemoteArtwork,
)
from piperch.paths import AppPaths
from piperch.services.downloads import (
    ArtworkDownloadService,
    DownloadCancellation,
    DownloadCancelledError,
)
from piperch.services.thumbnails import ArtworkThumbnailCache

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pytest import MonkeyPatch

    from piperch.pixiv import PixivClient
    from piperch.repositories import ArtworkRepository
    from piperch.settings import SettingsManager


class StubSettings:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def get(self) -> AppSettings:
        return self._settings


class StubArtworkRepository:
    def __init__(self) -> None:
        self.saved_media: tuple[MediaRecord, ...] | None = None

    def is_complete(self, _artwork_id: int, _library_root: Path) -> bool:
        return False

    def find_existing_ids(self, _artwork_ids: Sequence[int]) -> set[int]:
        return set()

    def list_media(self, _artwork_id: int) -> tuple[MediaRecord, ...]:
        return ()

    def save_download(self, _artwork: RemoteArtwork, media: Sequence[MediaRecord]) -> None:
        self.saved_media = tuple(media)


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

    async def get_artwork(self, artwork_id: int, _cookie: str | None) -> RemoteArtwork:
        assert artwork_id == self._artwork.artwork_id
        return self._artwork

    async def download(self, _url: str, target: Path, _cookie: str | None) -> tuple[str, int]:
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
    )

    result = await service.download_artwork(123, "job-id", DownloadCancellation())

    assert result is ItemState.SUCCEEDED
    assert pixiv.maximum_active_downloads == 1
    assert qualities == ([67, 67, 67] if webp_enabled else [])
    assert repository.saved_media is not None
    media = repository.saved_media[0]
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
    service = ArtworkDownloadService(
        paths,
        cast("SettingsManager", StubSettings(settings)),
        cast("ArtworkRepository", repository),
        cast("PixivClient", StubPixivClient(artwork)),
        FailingThumbnailCache(paths),
    )

    result = await service.download_artwork(123, "job-id", DownloadCancellation())

    assert result is ItemState.SUCCEEDED
    assert repository.saved_media is not None
    assert (settings.library_root / repository.saved_media[0].relative_path).is_file()


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
    cancellation = DownloadCancellation()

    def request_cancel() -> None:
        cancellation.request()

    service = ArtworkDownloadService(
        paths,
        cast("SettingsManager", StubSettings(settings)),
        cast("ArtworkRepository", repository),
        cast("PixivClient", StubPixivClient(artwork, request_cancel)),
    )

    with pytest.raises(DownloadCancelledError):
        await service.download_artwork(123, "job-id", cancellation)

    assert repository.saved_media is None
    assert not (settings.library_root / "456" / "123").exists()
