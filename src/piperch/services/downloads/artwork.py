from __future__ import annotations

import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from anyio import to_thread
from PIL import Image, ImageOps

from piperch.domain import ArtworkType, ItemState, MediaRecord, RemoteArtwork
from piperch.errors import AppError, UpstreamError
from piperch.repositories.groups import validate_imported_group_names
from piperch.services.library_files import LibraryFileOperations
from piperch.services.thumbnails import ArtworkThumbnailCache

if TYPE_CHECKING:
    from collections.abc import Sequence

    from piperch.paths import AppPaths
    from piperch.pixiv import PixivClient
    from piperch.repositories import ArtworkRepository
    from piperch.services.downloads.cancellation import DownloadCancellation
    from piperch.services.downloads.commit import ArtworkDownloadCommitService
    from piperch.settings import SettingsManager

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
logger = logging.getLogger(__name__)


class ArtworkDownloadService:
    def __init__(
        self,
        paths: AppPaths,
        settings: SettingsManager,
        artworks: ArtworkRepository,
        pixiv: PixivClient,
        commits: ArtworkDownloadCommitService,
        thumbnails: ArtworkThumbnailCache | None = None,
        files: LibraryFileOperations | None = None,
    ) -> None:
        self._settings = settings
        self._artworks = artworks
        self._pixiv = pixiv
        self._commits = commits
        self._thumbnails = thumbnails or ArtworkThumbnailCache(paths)
        self._files = files or LibraryFileOperations()

    async def download_artwork(
        self,
        artwork_id: int,
        job_id: str,
        cancellation: DownloadCancellation,
    ) -> ItemState:
        settings = await to_thread.run_sync(self._settings.get)
        if await to_thread.run_sync(
            self._artworks.is_complete,
            artwork_id,
            settings.library_root,
        ):
            return ItemState.SKIPPED
        cancellation.raise_if_requested()

        is_new_artwork = not await to_thread.run_sync(
            lambda: artwork_id in self._artworks.find_existing_ids((artwork_id,))
        )
        artwork = await self._pixiv.get_artwork(artwork_id, settings.pixiv_cookie)
        cancellation.raise_if_requested()
        bookmark_tags: tuple[str, ...] | None = None
        if is_new_artwork and artwork.bookmark_data is not None and not artwork.bookmark_data.private:
            try:
                bookmark = await self._pixiv.get_public_bookmark(
                    artwork_id,
                    artwork.bookmark_data.bookmark_id,
                    settings.pixiv_cookie,
                )
                bookmark_tags = validate_imported_group_names(bookmark.tags)
            except AppError as error:
                logger.warning(
                    "作品 %d 的 Pixiv 收藏标签导入失败，媒体将继续入库: %s",
                    artwork_id,
                    error.message,
                )
        cancellation.raise_if_requested()
        existing_media = await to_thread.run_sync(self._artworks.list_media, artwork_id)
        stage = self._files.download_stage(settings.library_root, job_id, artwork_id)
        try:
            await to_thread.run_sync(self._prepare_stage, stage)
            cancellation.raise_if_requested()
            media = await self._download_media(
                artwork,
                stage,
                settings.webp_enabled,
                settings.webp_quality,
                cancellation,
                existing_media,
                settings.library_root,
            )
            cancellation.raise_if_requested()
            await to_thread.run_sync(self._validate_stage, artwork, stage)
            cancellation.raise_if_requested()
            final_dir = settings.library_root / str(artwork.author_id) / str(artwork_id)
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
            # 文件发布后必须完成元数据提交与备份清理，取消只在此提交边界之前生效。
            published = await to_thread.run_sync(self._files.publish, stage, final_dir)
            try:
                if bookmark_tags is None:
                    await to_thread.run_sync(self._commits.commit, artwork, final_media)
                else:
                    await to_thread.run_sync(
                        self._commits.commit,
                        artwork,
                        final_media,
                        bookmark_tags,
                    )
            except Exception:
                await to_thread.run_sync(published.rollback)
                raise
            await to_thread.run_sync(published.finalize)
            try:
                await to_thread.run_sync(self._create_thumbnails, artwork_id, final_dir, final_media)
            except Exception:
                logger.exception("作品 %d 缩略图缓存生成失败，将在访问时重试。", artwork_id)
            return ItemState.SUCCEEDED
        finally:
            await to_thread.run_sync(self._files.cleanup_download_stage, settings.library_root, stage)

    async def _download_media(
        self,
        artwork: RemoteArtwork,
        stage: Path,
        webp_enabled: bool,
        webp_quality: int,
        cancellation: DownloadCancellation,
        existing_media: Sequence[MediaRecord],
        library_root: Path,
    ) -> tuple[MediaRecord, ...]:
        records: list[MediaRecord] = []
        cancellation.raise_if_requested()
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
                if not webp_enabled and reused_cover.mime_type == "image/webp":
                    (stage / Path(reused_cover.relative_path).name).unlink()
                    reused_cover = None
                else:
                    records.append(
                        await self._finalize_image(
                            stage / Path(reused_cover.relative_path).name,
                            reused_cover.mime_type,
                            reused_cover.byte_size,
                            "cover",
                            None,
                            webp_enabled and reused_cover.mime_type != "image/webp",
                            webp_quality,
                        )
                    )
            if reused_cover is None:
                cover = stage / (f"{artwork.artwork_id}_cover{self._extension(cover_url, '.jpg')}")
                cancellation.raise_if_requested()
                mime, size = await self._pixiv.download(cover_url, cover)
                cancellation.raise_if_requested()
                self._require_media_type(mime, "image/", "Ugoira 封面")
                records.append(
                    await self._finalize_image(
                        cover,
                        mime,
                        size,
                        "cover",
                        None,
                        webp_enabled,
                        webp_quality,
                    )
                )
            cancellation.raise_if_requested()
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
                cancellation.raise_if_requested()
                mime, size = await self._pixiv.download(artwork.ugoira_zip_url, archive)
                cancellation.raise_if_requested()
                if mime not in {"application/zip", "application/octet-stream"}:
                    raise UpstreamError("invalid_media_type", "Ugoira ZIP 的媒体类型无效。")
                records.append(MediaRecord("ugoiraZip", archive.name, mime, size))
            cancellation.raise_if_requested()
            await to_thread.run_sync(self._validate_zip, archive, artwork)
            cancellation.raise_if_requested()
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

        async def download_page(page_index: int, url: str) -> MediaRecord:
            cancellation.raise_if_requested()
            reused = await to_thread.run_sync(
                self._reuse_media,
                existing_media,
                "page",
                page_index,
                library_root,
                stage,
            )
            if reused is not None:
                if not webp_enabled and reused.mime_type == "image/webp":
                    (stage / Path(reused.relative_path).name).unlink()
                else:
                    finalized = await self._finalize_image(
                        stage / Path(reused.relative_path).name,
                        reused.mime_type,
                        reused.byte_size,
                        "page",
                        page_index,
                        webp_enabled and reused.mime_type != "image/webp",
                        webp_quality,
                    )
                    cancellation.raise_if_requested()
                    return finalized
            cancellation.raise_if_requested()
            target = stage / (f"{artwork.artwork_id}_p{page_index}{self._extension(url, '.jpg')}")
            mime, size = await self._pixiv.download(url, target)
            cancellation.raise_if_requested()
            self._require_media_type(mime, "image/", "作品原图")
            finalized = await self._finalize_image(
                target,
                mime,
                size,
                "page",
                page_index,
                webp_enabled,
                webp_quality,
            )
            cancellation.raise_if_requested()
            return finalized

        for index, url in enumerate(artwork.original_urls):
            records.append(await download_page(index, url))
        return tuple(records)

    @staticmethod
    async def _finalize_image(
        source: Path,
        mime_type: str,
        byte_size: int,
        role: str,
        page_index: int | None,
        transcode: bool,
        webp_quality: int,
    ) -> MediaRecord:
        if transcode:
            source, byte_size = await to_thread.run_sync(
                ArtworkDownloadService._transcode_to_webp,
                source,
                webp_quality,
            )
            mime_type = "image/webp"
        return MediaRecord(role, source.name, mime_type, byte_size, page_index)

    @staticmethod
    def _transcode_to_webp(source: Path, quality: int) -> tuple[Path, int]:
        """以临时文件完成 WebP 转码，成功后再移除原文件。"""
        target = source.with_suffix(".webp")
        temporary = target.with_name(f"{target.name}.part")
        temporary.unlink(missing_ok=True)
        try:
            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened)
                has_alpha = "A" in image.getbands() or "transparency" in image.info
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if has_alpha else "RGB")
                image.save(temporary, "WEBP", quality=quality, method=4)
            temporary.replace(target)
        except (OSError, ValueError) as error:
            temporary.unlink(missing_ok=True)
            raise UpstreamError("webp_conversion_failed", f"图片 {source.name} 转码为 WebP 失败。") from error
        if source != target:
            source.unlink()
        return target, target.stat().st_size

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

    def _create_thumbnails(
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
        self._thumbnails.create_cover_thumbnail(artwork_id, source)
        self._thumbnails.create_page_thumbnails(artwork_id, final_dir, media)
