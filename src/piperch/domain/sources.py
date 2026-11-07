from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ArtworkSource(StrEnum):
    PIXIV = "pixiv"
    FANBOX = "fanbox"


@dataclass(frozen=True, slots=True)
class LibraryArtworkReference:
    local_artwork_id: int
    source: ArtworkSource
    remote_id: int


def artwork_directory(root: Path, source: ArtworkSource, author_id: int, remote_id: int) -> Path:
    """保留既有 Pixiv 目录，并将 FANBOX 图片放入独立来源目录。"""
    base = root if source is ArtworkSource.PIXIV else root / source.value
    return base / str(author_id) / str(remote_id)
