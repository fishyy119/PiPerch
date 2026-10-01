from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest

from piperch.domain import DownloadItemRecord, DownloadProgressPhase, ItemState
from piperch.services.downloads import DownloadEventBroker, DownloadSupervisor

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from piperch.repositories import DownloadRepository
    from piperch.services.downloads import ArtworkDownloadService


class BlockingRepository:
    def __init__(self) -> None:
        self.claimed = False

    def recover_interrupted(self) -> None:
        pass

    def claim_next(self) -> tuple[str, DownloadItemRecord] | None:
        if self.claimed:
            return None
        self.claimed = True
        return (
            "job-id",
            DownloadItemRecord(
                item_id=1,
                artwork_id=123,
                state=ItemState.RUNNING,
                attempts=1,
                error=None,
            ),
        )

    def is_cancel_requested(self, _job_id: str) -> bool:
        return False


class BlockingDownloadService:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def download_artwork(self, *_args: object, **_kwargs: object) -> ItemState:
        self.started.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.cancelled.set()
        return ItemState.SUCCEEDED


class ProgressRepository(BlockingRepository):
    def __init__(self) -> None:
        super().__init__()
        self.progress: list[tuple[DownloadProgressPhase, int, int | None]] = []
        self.completed_state: ItemState | None = None

    def update_item_progress(
        self,
        _item_id: int,
        phase: DownloadProgressPhase,
        completed_pages: int,
        total_pages: int | None,
    ) -> None:
        self.progress.append((phase, completed_pages, total_pages))

    def complete_item(self, _item_id: int, state: ItemState, _error: str | None = None) -> None:
        self.completed_state = state


class ProgressDownloadService:
    def __init__(self) -> None:
        self.finished = asyncio.Event()

    async def download_artwork(
        self,
        _artwork_id: int,
        _job_id: str,
        _is_cancel_requested: object,
        report_progress: object,
    ) -> ItemState:
        reporter = cast("Callable[[DownloadProgressPhase, int, int | None], Awaitable[None]]", report_progress)
        await reporter(DownloadProgressPhase.DOWNLOADING, 0, 3)
        await reporter(DownloadProgressPhase.DOWNLOADING, 1, 3)
        await reporter(DownloadProgressPhase.DOWNLOADING, 2, 3)
        await reporter(DownloadProgressPhase.DOWNLOADING, 3, 3)
        await reporter(DownloadProgressPhase.FINALIZING, 3, 3)
        self.finished.set()
        return ItemState.SUCCEEDED


@pytest.mark.asyncio
async def test_stop_cancels_an_active_download() -> None:
    repository = BlockingRepository()
    service = BlockingDownloadService()
    supervisor = DownloadSupervisor(
        cast("DownloadRepository", repository),
        cast("ArtworkDownloadService", service),
        DownloadEventBroker(),
    )

    await supervisor.start()
    await asyncio.wait_for(service.started.wait(), timeout=1)
    await asyncio.wait_for(supervisor.stop(), timeout=1)

    assert service.cancelled.is_set()
    await supervisor.stop()


@pytest.mark.asyncio
async def test_supervisor_persists_page_progress() -> None:
    repository = ProgressRepository()
    service = ProgressDownloadService()
    supervisor = DownloadSupervisor(
        cast("DownloadRepository", repository),
        cast("ArtworkDownloadService", service),
        DownloadEventBroker(),
    )

    await supervisor.start()
    await asyncio.wait_for(service.finished.wait(), timeout=1)
    for _ in range(100):
        if repository.completed_state is not None:
            break
        await asyncio.sleep(0.01)
    await supervisor.stop()

    assert repository.progress == [
        (DownloadProgressPhase.DOWNLOADING, 0, 3),
        (DownloadProgressPhase.DOWNLOADING, 1, 3),
        (DownloadProgressPhase.DOWNLOADING, 2, 3),
        (DownloadProgressPhase.DOWNLOADING, 3, 3),
        (DownloadProgressPhase.FINALIZING, 3, 3),
    ]
    assert repository.completed_state is ItemState.SUCCEEDED
