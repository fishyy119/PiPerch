from __future__ import annotations

import asyncio
import json
import math
from collections.abc import AsyncIterator

from anyio import to_thread
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from piperch.api.converters import download_job_detail_response, download_job_summary_response
from piperch.api.dependencies import get_container
from piperch.api.models import (
    DownloadJobCreate,
    DownloadJobCreated,
    DownloadJobDetailResponse,
    DownloadJobPage,
)
from piperch.container import AppContainer

router = APIRouter(prefix="/download-jobs", tags=["downloads"])
events_router = APIRouter(prefix="/events", tags=["downloads"])


@router.post("", response_model=DownloadJobCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: DownloadJobCreate,
    container: AppContainer = Depends(get_container),
) -> DownloadJobCreated:
    container.storage.require_available()
    job_id = await to_thread.run_sync(
        container.downloads.create_job,
        request.artwork_ids,
        request.source_label,
    )
    container.supervisor.notify()
    await container.events.publish(job_id)
    return DownloadJobCreated(job_id=job_id)


@router.get("", response_model=DownloadJobPage)
def list_jobs(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    container: AppContainer = Depends(get_container),
) -> DownloadJobPage:
    jobs, total = container.downloads.list_jobs(page, size)
    return DownloadJobPage(
        items=[download_job_summary_response(job) for job in jobs],
        page=page,
        size=size,
        total_elements=total,
        total_pages=math.ceil(total / size),
    )


@router.get("/{job_id}", response_model=DownloadJobDetailResponse)
def get_job(
    job_id: str,
    container: AppContainer = Depends(get_container),
) -> DownloadJobDetailResponse:
    return download_job_detail_response(container.downloads.get_job(job_id))


@router.post("/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_job(
    job_id: str,
    container: AppContainer = Depends(get_container),
) -> None:
    await to_thread.run_sync(container.downloads.request_cancel, job_id)
    container.supervisor.notify()
    await container.events.publish(job_id)


@router.post("/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: str,
    container: AppContainer = Depends(get_container),
) -> None:
    container.storage.require_available()
    await to_thread.run_sync(container.downloads.retry, job_id)
    container.supervisor.notify()
    await container.events.publish(job_id)


async def _event_stream(request: Request, container: AppContainer) -> AsyncIterator[str]:
    yield "retry: 2000\n\n"
    async with container.events.subscribe() as queue:
        while not await request.is_disconnected():
            try:
                job_id = await asyncio.wait_for(queue.get(), timeout=15)
            except TimeoutError:
                yield ": heartbeat\n\n"
                continue
            data = json.dumps({"jobId": job_id})
            yield f"event: job-updated\ndata: {data}\n\n"


@events_router.get("/downloads", response_class=StreamingResponse)
async def download_events(
    request: Request,
    container: AppContainer = Depends(get_container),
) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request, container),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
