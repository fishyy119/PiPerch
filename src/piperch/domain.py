from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ArtworkType(StrEnum):
    ILLUST = "illust"
    MANGA = "manga"
    UGOIRA = "ugoira"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partiallySucceeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ItemState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SKIPPED = "skipped"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AppSettings:
    pixiv_cookie: str | None
    proxy_url: str | None
    library_root: Path
    download_concurrency: int
    request_interval_ms: int
    webp_enabled: bool
    webp_quality: int


@dataclass(frozen=True, slots=True)
class TagRecord:
    name: str
    translated_name: str | None = None


@dataclass(frozen=True, slots=True)
class UgoiraFrame:
    file_name: str
    delay_ms: int


@dataclass(frozen=True, slots=True)
class RemoteArtwork:
    artwork_id: int
    artwork_type: ArtworkType
    title: str
    description: str
    author_id: int
    author_name: str
    author_account: str | None
    author_avatar_url: str | None
    series_id: int | None
    series_title: str | None
    page_count: int
    width: int | None
    height: int | None
    x_restrict: int
    is_ai: bool
    published_at: str | None
    original_urls: tuple[str, ...]
    thumbnail_url: str | None
    ugoira_zip_url: str | None = None
    ugoira_frames: tuple[UgoiraFrame, ...] = ()
    tags: tuple[TagRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class MediaRecord:
    role: str
    relative_path: str
    mime_type: str
    byte_size: int
    page_index: int | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    artwork_id: int
    title: str
    author_name: str
    artwork_type: ArtworkType
    page_count: int
    x_restrict: int
    is_ai: bool
    thumbnail_url: str | None


@dataclass(frozen=True, slots=True)
class FollowedUser:
    user_id: int
    name: str
    avatar_url: str | None


@dataclass(frozen=True, slots=True)
class ArtworkSummary:
    artwork_id: int
    title: str
    artwork_type: ArtworkType
    author_id: int
    author_name: str
    series_id: int | None
    series_title: str | None
    page_count: int
    x_restrict: int
    is_ai: bool
    published_at: str | None
    downloaded_at: str
    tags: tuple[tuple[int, TagRecord], ...] = ()


@dataclass(frozen=True, slots=True)
class ArtworkDetail:
    summary: ArtworkSummary
    description: str
    width: int | None
    height: int | None
    media: tuple[MediaRecord, ...]
    ugoira_frames: tuple[UgoiraFrame, ...]


@dataclass(frozen=True, slots=True)
class NamedCount:
    item_id: int
    name: str
    count: int
    subtitle: str | None = None


@dataclass(frozen=True, slots=True)
class DownloadItemRecord:
    item_id: int
    artwork_id: int
    state: ItemState
    attempts: int
    error: str | None


@dataclass(frozen=True, slots=True)
class DownloadJobRecord:
    job_id: str
    source_label: str
    state: JobState
    cancel_requested: bool
    created_at: str
    started_at: str | None
    finished_at: str | None
    error_summary: str | None
    counts: dict[ItemState, int] = field(default_factory=lambda: {})
    items: tuple[DownloadItemRecord, ...] = ()
