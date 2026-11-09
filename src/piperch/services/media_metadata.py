from __future__ import annotations

import logging
import zipfile
from typing import TYPE_CHECKING

from PIL import ExifTags, Image
from sqlalchemy import and_, or_, select, update

from piperch.database.tables import media_files, ugoira_frames
from piperch.repositories._rows import integer, optional_string, string

if TYPE_CHECKING:
    from pathlib import Path

    from piperch.database import Database

logger = logging.getLogger(__name__)
_BACKFILL_BATCH_SIZE = 128


def image_dimensions(source: Path) -> tuple[int, int]:
    """读取文件元数据，取得按 EXIF 方向显示的图片尺寸。"""
    with Image.open(source) as image:
        width, height = image.size
        if image.getexif().get(ExifTags.Base.Orientation) in {5, 6, 7, 8}:
            width, height = height, width
    return width, height


def ugoira_dimensions(source: Path, first_frame: str) -> tuple[int, int]:
    """读取时序首帧的尺寸，与生成动态 WebP 时使用的画布一致。"""
    with zipfile.ZipFile(source) as archive, archive.open(first_frame) as entry, Image.open(entry) as image:
        return image.size


def backfill_media_dimensions(database: Database, library_root: Path) -> None:
    """启动时分批补齐旧图片与动图尺寸，已提交的批次可在下次启动时跳过。"""
    root = library_root.resolve()
    cursor = 0
    completed = 0
    failed = 0
    while True:
        with database.connect() as connection:
            rows = (
                connection.execute(
                    select(media_files.c.id, media_files.c.relative_path, media_files.c.role, ugoira_frames.c.file_name)
                    .select_from(
                        media_files.outerjoin(
                            ugoira_frames,
                            and_(media_files.c.artwork_id == ugoira_frames.c.artwork_id, ugoira_frames.c.sequence == 0),
                        )
                    )
                    .where(
                        media_files.c.id > cursor,
                        or_(
                            and_(
                                media_files.c.role.in_(("page", "cover")),
                                media_files.c.mime_type.startswith("image/"),
                            ),
                            media_files.c.role == "ugoiraZip",
                        ),
                        or_(media_files.c.width.is_(None), media_files.c.height.is_(None)),
                    )
                    .order_by(media_files.c.id)
                    .limit(_BACKFILL_BATCH_SIZE)
                )
                .mappings()
                .all()
            )
        if not rows:
            break
        dimensions: list[tuple[int, int, int]] = []
        for row in rows:
            cursor = integer(row["id"])
            relative_path = string(row["relative_path"])
            try:
                source = (root / relative_path).resolve()
                if root not in source.parents:
                    raise ValueError("媒体路径超出图库目录。")
                if string(row["role"]) == "ugoiraZip":
                    first_frame = optional_string(row["file_name"])
                    if first_frame is None:
                        raise ValueError("动图缺少首帧信息。")
                    width, height = ugoira_dimensions(source, first_frame)
                else:
                    width, height = image_dimensions(source)
            except (OSError, ValueError, KeyError, zipfile.BadZipFile, Image.DecompressionBombError):
                failed += 1
                logger.warning("无法补齐媒体 %s 的尺寸，将保留占位比例。", relative_path, exc_info=True)
                continue
            dimensions.append((cursor, width, height))
        with database.begin() as connection:
            for media_id, width, height in dimensions:
                connection.execute(
                    update(media_files).where(media_files.c.id == media_id).values(width=width, height=height)
                )
        completed += len(dimensions)
        logger.info("媒体尺寸补齐进度: 已完成 %d 张，跳过 %d 张。", completed, failed)
