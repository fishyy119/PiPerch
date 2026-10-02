from __future__ import annotations

import logging
import shutil
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import TYPE_CHECKING, ClassVar

from PIL import Image, ImageOps

if TYPE_CHECKING:
    from collections.abc import Sequence

    from piperch.domain import MediaRecord
    from piperch.paths import AppPaths

logger = logging.getLogger(__name__)

_THUMBNAIL_WEBP_QUALITY = 75
_COVER_THUMBNAIL_SIZE = 512
_PAGE_THUMBNAIL_SIZE = 256
_PAGE_GENERATION_CONCURRENCY = 2


class ArtworkThumbnailCache:
    """管理可由本地原图重新生成的作品缩略图缓存。"""

    _PAGE_LOCK_COUNT: ClassVar[int] = 16

    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths
        self._generation_slots = BoundedSemaphore(_PAGE_GENERATION_CONCURRENCY)
        self._page_locks = tuple(Lock() for _ in range(self._PAGE_LOCK_COUNT))

    def create_cover_thumbnail(self, artwork_id: int, source: Path) -> Path:
        target = self._paths.thumbnails / f"{artwork_id}.webp"
        self._write_thumbnail(source, target, _COVER_THUMBNAIL_SIZE)
        return target

    def ensure_page_thumbnail(self, artwork_id: int, page_index: int, source: Path) -> Path:
        target = self.page_thumbnail_path(artwork_id, page_index)
        if self._is_fresh(target, source):
            return target

        lock = self._page_locks[hash((artwork_id, page_index)) % self._PAGE_LOCK_COUNT]
        with lock:
            if self._is_fresh(target, source):
                return target
            with self._generation_slots:
                self._write_thumbnail(source, target, _PAGE_THUMBNAIL_SIZE)
        return target

    def create_page_thumbnails(
        self,
        artwork_id: int,
        final_dir: Path,
        media: Sequence[MediaRecord],
    ) -> None:
        expected_indexes: set[int] = set()
        for item in media:
            if item.role != "page" or item.page_index is None:
                continue
            expected_indexes.add(item.page_index)
            source = final_dir / Path(item.relative_path).name
            try:
                self.ensure_page_thumbnail(artwork_id, item.page_index, source)
            except (OSError, ValueError):
                logger.exception("作品 %d 第 %d 页缩略图生成失败。", artwork_id, item.page_index)

        page_directory = self.page_thumbnail_directory(artwork_id)
        if page_directory.is_dir():
            for target in page_directory.glob("*.webp"):
                if not target.stem.isdecimal() or int(target.stem) not in expected_indexes:
                    target.unlink(missing_ok=True)

    def delete_artwork(self, artwork_id: int) -> None:
        (self._paths.thumbnails / f"{artwork_id}.webp").unlink(missing_ok=True)
        shutil.rmtree(self.page_thumbnail_directory(artwork_id), ignore_errors=True)

    def page_thumbnail_path(self, artwork_id: int, page_index: int) -> Path:
        return self.page_thumbnail_directory(artwork_id) / f"{page_index}.webp"

    def page_thumbnail_directory(self, artwork_id: int) -> Path:
        return self._paths.thumbnails / "pages" / str(artwork_id)

    @staticmethod
    def _is_fresh(target: Path, source: Path) -> bool:
        return target.is_file() and target.stat().st_mtime_ns >= source.stat().st_mtime_ns

    @staticmethod
    def _write_thumbnail(source: Path, target: Path, maximum_size: int) -> None:
        temporary = target.with_suffix(".webp.part")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.unlink(missing_ok=True)
        try:
            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened)
                image.thumbnail((maximum_size, maximum_size))
                has_alpha = "A" in image.getbands() or "transparency" in image.info
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if has_alpha else "RGB")
                image.save(temporary, "WEBP", quality=_THUMBNAIL_WEBP_QUALITY, method=4)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
