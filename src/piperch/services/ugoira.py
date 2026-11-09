from __future__ import annotations

import shutil
import zipfile
from contextlib import ExitStack
from hashlib import sha256
from threading import BoundedSemaphore, Lock
from typing import TYPE_CHECKING

from PIL import Image

from piperch.errors import AppError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from piperch.domain.artworks import UgoiraFrame
    from piperch.paths import AppPaths


class UgoiraAnimationCache:
    """由本地 ZIP 和帧时序生成可重建的动态 WebP 缓存。"""

    def __init__(self, paths: AppPaths) -> None:
        self._directory = paths.data_dir / "cache" / "ugoira"
        self._locks = tuple(Lock() for _ in range(16))
        # 动图需要解码多帧，限制同时编码的数量以控制内存占用。
        self._generation_slot = BoundedSemaphore(1)

    def ensure_animation(self, artwork_id: int, source: Path, frames: Sequence[UgoiraFrame], quality: int) -> Path:
        source_stat = source.stat()
        signature = repr(
            (
                "webp-v1",
                str(source.resolve()),
                source_stat.st_mtime_ns,
                source_stat.st_size,
                quality,
                tuple((frame.file_name, frame.delay_ms) for frame in frames),
            )
        )
        target = self._directory / str(artwork_id) / f"{sha256(signature.encode()).hexdigest()}.webp"
        with self._locks[artwork_id % len(self._locks)]:
            if target.is_file():
                return target
            with self._generation_slot:
                self._write_animation(source, target, frames, quality)
        return target

    def delete_artwork(self, artwork_id: int) -> None:
        with self._locks[artwork_id % len(self._locks)]:
            shutil.rmtree(self._directory / str(artwork_id), ignore_errors=True)

    @staticmethod
    def _write_animation(source: Path, target: Path, frames: Sequence[UgoiraFrame], quality: int) -> None:
        temporary = target.with_suffix(".webp.part")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.unlink(missing_ok=True)
        try:
            if not frames:
                raise ValueError("动图缺少帧信息。")
            with ExitStack() as resources:
                archive = resources.enter_context(zipfile.ZipFile(source))
                images: list[Image.Image] = []
                for frame in frames:
                    with archive.open(frame.file_name) as entry, Image.open(entry) as opened:
                        image = resources.enter_context(opened.convert("RGBA"))
                    images.append(image)
                images[0].save(
                    temporary,
                    "WEBP",
                    save_all=True,
                    append_images=images[1:],
                    duration=[frame.delay_ms for frame in frames],
                    loop=0,
                    quality=quality,
                    method=4,
                )
            temporary.replace(target)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
            raise AppError("ugoira_conversion_failed", "Ugoira 转码为 WebP 失败。", 500) from error
        finally:
            temporary.unlink(missing_ok=True)
