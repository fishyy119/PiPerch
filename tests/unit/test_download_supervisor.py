from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest

from piperch.domain import DownloadItemRecord, ItemState
from piperch.services.downloads import DownloadEventBroker, DownloadSupervisor

if TYPE_CHECKING:
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
