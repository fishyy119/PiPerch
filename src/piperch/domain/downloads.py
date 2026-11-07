from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from piperch.domain.sources import ArtworkSource


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
class DownloadItemRecord:
    item_id: int
    remote_id: int
    state: ItemState
    attempts: int
    error: str | None
    source: ArtworkSource = ArtworkSource.PIXIV
    author_id: int | None = None


@dataclass(frozen=True, slots=True)
class DownloadJobSummary:
    job_id: str
    source_label: str
    state: JobState
    cancel_requested: bool
    created_at: str
    started_at: str | None
    finished_at: str | None
    error_summary: str | None
    counts: dict[ItemState, int]


@dataclass(frozen=True, slots=True)
class DownloadJobDetail:
    summary: DownloadJobSummary
    items: tuple[DownloadItemRecord, ...]
