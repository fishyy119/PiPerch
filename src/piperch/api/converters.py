from __future__ import annotations

from piperch.api.models import (
    ArtworkDetailResponse,
    ArtworkSummaryResponse,
    DownloadItemResponse,
    DownloadJobDetailResponse,
    DownloadJobSummaryResponse,
    DownloadProgressResponse,
    JobCounts,
    MediaResponse,
    TagResponse,
    UgoiraFrameResponse,
)
from piperch.domain import ArtworkDetail, ArtworkSummary, DownloadJobRecord, ItemState


def artwork_summary_response(summary: ArtworkSummary) -> ArtworkSummaryResponse:
    return ArtworkSummaryResponse(
        artwork_id=summary.artwork_id,
        title=summary.title,
        artwork_type=summary.artwork_type,
        author_id=summary.author_id,
        author_name=summary.author_name,
        series_id=summary.series_id,
        series_title=summary.series_title,
        page_count=summary.page_count,
        x_restrict=summary.x_restrict,
        is_ai=summary.is_ai,
        published_at=summary.published_at,
        downloaded_at=summary.downloaded_at,
    )


def artwork_detail_response(detail: ArtworkDetail) -> ArtworkDetailResponse:
    return ArtworkDetailResponse(
        **artwork_summary_response(detail.summary).model_dump(),
        description=detail.description,
        width=detail.width,
        height=detail.height,
        tags=[
            TagResponse(
                tag_id=tag_id,
                name=tag.name,
                translated_name=tag.translated_name,
            )
            for tag_id, tag in detail.summary.tags
        ],
        media=[
            MediaResponse(
                role=item.role,
                page_index=item.page_index,
                mime_type=item.mime_type,
                byte_size=item.byte_size,
            )
            for item in detail.media
        ],
        ugoira_frames=[
            UgoiraFrameResponse(file_name=item.file_name, delay_ms=item.delay_ms) for item in detail.ugoira_frames
        ],
    )


def download_job_summary_response(job: DownloadJobRecord) -> DownloadJobSummaryResponse:
    return DownloadJobSummaryResponse(
        job_id=job.job_id,
        source_label=job.source_label,
        state=job.state,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_summary=job.error_summary,
        counts=JobCounts(
            queued=job.counts.get(ItemState.QUEUED, 0),
            running=job.counts.get(ItemState.RUNNING, 0),
            skipped=job.counts.get(ItemState.SKIPPED, 0),
            succeeded=job.counts.get(ItemState.SUCCEEDED, 0),
            failed=job.counts.get(ItemState.FAILED, 0),
            cancelled=job.counts.get(ItemState.CANCELLED, 0),
        ),
        progress=(
            DownloadProgressResponse(
                current_artwork_id=job.progress.current_artwork_id,
                completed_pages=job.progress.completed_pages,
                total_pages=job.progress.total_pages,
                phase=job.progress.phase,
            )
            if job.progress is not None
            else None
        ),
    )


def download_job_detail_response(job: DownloadJobRecord) -> DownloadJobDetailResponse:
    return DownloadJobDetailResponse(
        **download_job_summary_response(job).model_dump(),
        items=[
            DownloadItemResponse(
                item_id=item.item_id,
                artwork_id=item.artwork_id,
                state=item.state,
                attempts=item.attempts,
                error=item.error,
            )
            for item in job.items
        ],
    )
