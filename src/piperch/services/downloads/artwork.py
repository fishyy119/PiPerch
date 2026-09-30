from __future__ import annotations

import asyncio
import json
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

from anyio import to_thread
from PIL import Image

from piperch.domain import ArtworkType, ItemState, MediaRecord, RemoteArtwork
from piperch.errors import UpstreamError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from piperch.paths import AppPaths
    from piperch.pixiv import PixivClient
    from piperch.repositories import ArtworkRepository
    from piperch.settings import SettingsManager

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class DownloadCancelledError(Exception):
    """任务取消后中断尚未开始的媒体请求。"""


class ArtworkDownloadService:
    def __init__(
        self,
        paths: AppPaths,
        settings: SettingsManager,
        artworks: ArtworkRepository,
        pixiv: PixivClient,
    ) -> None:
        self._paths = paths
        self._settings = settings
        self._artworks = artworks
        self._pixiv = pixiv

    async def download_artwork(
        self,
        artwork_id: int,
        job_id: str,
        is_cancel_requested: Callable[[], Awaitable[bool]],
    ) -> ItemState:
        settings = await to_thread.run_sync(self._settings.get)
        if await to_thread.run_sync(
            self._artworks.is_complete,
            artwork_id,
            settings.library_root,
        ):
            return ItemState.SKIPPED

        artwork = await self._pixiv.get_artwork(artwork_id, settings.pixiv_cookie)
        await self._raise_if_cancelled(is_cancel_requested)
        existing_media = await to_thread.run_sync(self._artworks.list_media, artwork_id)
        stage = self._paths.staging / job_id / str(artwork_id)
        await to_thread.run_sync(self._prepare_stage, stage)
        try:
            media = await self._download_media(
                artwork,
                stage,
                settings.pixiv_cookie,
                settings.download_concurrency,
                is_cancel_requested,
                existing_media,
                settings.library_root,
            )
            await to_thread.run_sync(self._validate_stage, artwork, stage)
            final_dir = settings.library_root / str(artwork.author_id) / str(artwork_id)
            backup = await to_thread.run_sync(self._swap_stage, stage, final_dir)
            final_media = tuple(
                MediaRecord(
                    role=item.role,
                    page_index=item.page_index,
                    relative_path=str(
                        (final_dir / Path(item.relative_path).name).relative_to(settings.library_root)
                    ).replace("\\", "/"),
                    mime_type=item.mime_type,
                    byte_size=item.byte_size,
                )
                for item in media
            )
            try:
                await to_thread.run_sync(self._artworks.save_download, artwork, final_media)
                await to_thread.run_sync(self._create_thumbnail, artwork_id, final_dir, final_media)
            except Exception:
                await to_thread.run_sync(self._rollback_swap, final_dir, backup)
                raise
            if backup is not None:
                await to_thread.run_sync(shutil.rmtree, backup, True)
            return ItemState.SUCCEEDED
        finally:
            if stage.exists():
                await to_thread.run_sync(shutil.rmtree, stage, True)

    async def _download_media(
        self,
        artwork: RemoteArtwork,
        stage: Path,
        cookie: str | None,
        concurrency: int,
        is_cancel_requested: Callable[[], Awaitable[bool]],
        existing_media: Sequence[MediaRecord],
        library_root: Path,
    ) -> tuple[MediaRecord, ...]:
        records: list[MediaRecord] = []
        if artwork.artwork_type is ArtworkType.UGOIRA:
            cover_url = artwork.original_urls[0] if artwork.original_urls else artwork.thumbnail_url
            if not cover_url or not artwork.ugoira_zip_url:
                raise UpstreamError("ugoira_incomplete", "Pixiv 没有返回完整的 Ugoira 文件信息。")
            reused_cover = await to_thread.run_sync(
                self._reuse_media,
                existing_media,
                "cover",
                None,
                library_root,
                stage,
            )
            if reused_cover is not None:
                records.append(reused_cover)
            else:
                cover = stage / (f"{artwork.artwork_id}_cover{self._extension(cover_url, '.jpg')}")
                await self._raise_if_cancelled(is_cancel_requested)
                mime, size = await self._pixiv.download(cover_url, cover, cookie)
                self._require_media_type(mime, "image/", "Ugoira 封面")
                records.append(MediaRecord("cover", cover.name, mime, size))
            archive = stage / f"{artwork.artwork_id}_ugoira.zip"
            reused_archive = await to_thread.run_sync(
                self._reuse_media,
                existing_media,
                "ugoiraZip",
                None,
                library_root,
                stage,
            )
            if reused_archive is not None:
                archive = stage / Path(reused_archive.relative_path).name
                records.append(reused_archive)
            else:
                await self._raise_if_cancelled(is_cancel_requested)
                mime, size = await self._pixiv.download(artwork.ugoira_zip_url, archive, cookie)
                if mime not in {"application/zip", "application/octet-stream"}:
                    raise UpstreamError("invalid_media_type", "Ugoira ZIP 的媒体类型无效。")
                records.append(MediaRecord("ugoiraZip", archive.name, mime, size))
            await to_thread.run_sync(self._validate_zip, archive, artwork)
            metadata_path = stage / "ugoira.json"
            payload = {
                "artworkId": artwork.artwork_id,
                "frames": [{"file": frame.file_name, "delay": frame.delay_ms} for frame in artwork.ugoira_frames],
            }
            await to_thread.run_sync(
                metadata_path.write_text,
                json.dumps(payload, ensure_ascii=False, indent=2),
                "utf-8",
            )
            records.append(
                MediaRecord(
                    "ugoiraMetadata",
                    metadata_path.name,
                    "application/json",
                    metadata_path.stat().st_size,
                )
            )
            return tuple(records)

        if not artwork.original_urls:
            raise UpstreamError("missing_image_urls", "Pixiv 没有返回作品原图地址。")
        if len(artwork.original_urls) != artwork.page_count:
            raise UpstreamError(
                "incomplete_page_urls",
                f"Pixiv 返回了 {len(artwork.original_urls)}/{artwork.page_count} 个作品原图地址。",
            )
        semaphore = asyncio.Semaphore(concurrency)

        async def download_page(page_index: int, url: str) -> MediaRecord:
            async with semaphore:
                reused = await to_thread.run_sync(
                    self._reuse_media,
                    existing_media,
                    "page",
                    page_index,
                    library_root,
                    stage,
                )
                if reused is not None:
                    return reused
                await self._raise_if_cancelled(is_cancel_requested)
                target = stage / (f"{artwork.artwork_id}_p{page_index}{self._extension(url, '.jpg')}")
                mime, size = await self._pixiv.download(url, target, cookie)
                self._require_media_type(mime, "image/", "作品原图")
                return MediaRecord("page", target.name, mime, size, page_index)

        tasks = [asyncio.create_task(download_page(index, url)) for index, url in enumerate(artwork.original_urls)]
        try:
            return tuple(await asyncio.gather(*tasks))
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    @staticmethod
    async def _raise_if_cancelled(
        is_cancel_requested: Callable[[], Awaitable[bool]],
    ) -> None:
        if await is_cancel_requested():
            raise DownloadCancelledError

    @staticmethod
    def _require_media_type(mime_type: str, prefix: str, label: str) -> None:
        if not mime_type.lower().startswith(prefix):
            raise UpstreamError("invalid_media_type", f"{label}的媒体类型无效。")

    @staticmethod
    def _reuse_media(
        existing_media: Sequence[MediaRecord],
        role: str,
        page_index: int | None,
        library_root: Path,
        stage: Path,
    ) -> MediaRecord | None:
        record = next(
            (item for item in existing_media if item.role == role and item.page_index == page_index),
            None,
        )
        if record is None:
            return None
        source = (library_root / record.relative_path).resolve()
        root = library_root.resolve()
        if root not in source.parents or not source.is_file():
            return None
        if source.stat().st_size != record.byte_size:
            return None
        target = stage / source.name
        shutil.copy2(source, target)
        return MediaRecord(
            role=record.role,
            page_index=record.page_index,
            relative_path=target.name,
            mime_type=record.mime_type,
            byte_size=record.byte_size,
        )

    @staticmethod
    def _extension(url: str, fallback: str) -> str:
        suffix = Path(urlparse(url).path).suffix.lower()
        return suffix if suffix in _IMAGE_EXTENSIONS or suffix == ".zip" else fallback

    @staticmethod
    def _prepare_stage(stage: Path) -> None:
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)

    @staticmethod
    def _validate_zip(archive: Path, artwork: RemoteArtwork) -> None:
        try:
            with zipfile.ZipFile(archive) as handle:
                names = set(handle.namelist())
                damaged = handle.testzip()
        except zipfile.BadZipFile as error:
            raise UpstreamError("invalid_ugoira_zip", "Ugoira ZIP 文件无效。") from error
        if damaged:
            raise UpstreamError("invalid_ugoira_zip", f"Ugoira ZIP 中的 {damaged} 已损坏。")
        missing = [frame.file_name for frame in artwork.ugoira_frames if frame.file_name not in names]
        if missing:
            raise UpstreamError("invalid_ugoira_zip", "Ugoira ZIP 缺少帧文件。")

    @staticmethod
    def _validate_stage(artwork: RemoteArtwork, stage: Path) -> None:
        files = [path for path in stage.iterdir() if path.is_file()]
        if not files or any(path.stat().st_size <= 0 for path in files):
            raise UpstreamError("incomplete_stage", f"作品 {artwork.artwork_id} 的临时文件不完整。")

    @staticmethod
    def _swap_stage(stage: Path, final_dir: Path) -> Path | None:
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        backup: Path | None = None
        if final_dir.exists():
            backup = final_dir.with_name(f".{final_dir.name}.backup-{uuid4().hex}")
            final_dir.replace(backup)
        try:
            stage.replace(final_dir)
        except Exception:
            if backup is not None:
                backup.replace(final_dir)
            raise
        return backup

    @staticmethod
    def _rollback_swap(final_dir: Path, backup: Path | None) -> None:
        if final_dir.exists():
            shutil.rmtree(final_dir)
        if backup is not None and backup.exists():
            backup.replace(final_dir)

    def _create_thumbnail(
        self,
        artwork_id: int,
        final_dir: Path,
        media: Sequence[MediaRecord],
    ) -> None:
        source_record = next(
            (item for item in media if item.role in {"page", "cover"}),
            None,
        )
        if source_record is None:
            return
        source = final_dir / Path(source_record.relative_path).name
        target = self._paths.thumbnails / f"{artwork_id}.webp"
        temporary = target.with_suffix(".webp.part")
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            image.thumbnail((512, 512))
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            image.save(temporary, "WEBP", quality=82)
        temporary.replace(target)
