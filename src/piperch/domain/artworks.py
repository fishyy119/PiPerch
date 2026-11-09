from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from piperch.domain.sources import ArtworkSource

if TYPE_CHECKING:
    from piperch.domain.bookmarks import RemoteBookmarkReference


class ArtworkType(StrEnum):
    ILLUST = "illust"
    MANGA = "manga"
    UGOIRA = "ugoira"
    FANBOX = "fanbox"


@dataclass(frozen=True, slots=True)
class TagRecord:
    tag_id: int
    name: str


@dataclass(frozen=True, slots=True)
class TagSummary(TagRecord):
    artwork_count: int


@dataclass(frozen=True, slots=True)
class UgoiraFrame:
    file_name: str
    delay_ms: int


@dataclass(frozen=True, slots=True)
class RemoteArtwork:
    remote_id: int
    artwork_type: ArtworkType
    title: str
    description: str
    author_id: int
    author_name: str
    author_account: str | None
    series_id: int | None
    series_title: str | None
    page_count: int
    x_restrict: int | None
    is_ai: bool | None
    published_at: str | None
    original_urls: tuple[str, ...]
    thumbnail_url: str | None
    bookmark_data: RemoteBookmarkReference | None = None
    ugoira_zip_url: str | None = None
    ugoira_frames: tuple[UgoiraFrame, ...] = ()
    tags: tuple[str, ...] = ()
    source: ArtworkSource = ArtworkSource.PIXIV


@dataclass(frozen=True, slots=True)
class MediaRecord:
    role: str
    relative_path: str
    mime_type: str
    byte_size: int
    page_index: int | None = None
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class ArtworkImageSummary:
    artwork_id: int
    role: Literal["page", "ugoira"]
    page_index: int | None
    width: int | None
    height: int | None


@dataclass(frozen=True, slots=True)
class ArtworkSummary:
    artwork_id: int
    source: ArtworkSource
    remote_id: int
    title: str
    artwork_type: ArtworkType
    author_id: int
    author_name: str
    series_id: int | None
    series_title: str | None
    page_count: int
    x_restrict: int | None
    is_ai: bool | None
    published_at: str | None
    downloaded_at: str
    is_favorite: bool = False
    group_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ArtworkDetail:
    summary: ArtworkSummary
    description: str
    tags: tuple[TagRecord, ...]
    media: tuple[MediaRecord, ...]
    ugoira_frames: tuple[UgoiraFrame, ...]


@dataclass(frozen=True, slots=True)
class AuthorSummary:
    author_id: int
    name: str
    artwork_count: int


@dataclass(frozen=True, slots=True)
class SeriesSummary:
    series_id: int
    title: str
    author_name: str
    artwork_count: int
