from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import pytest

from piperch.domain import DownloadItemRecord, ItemState
from piperch.services.downloads import DownloadEventBroker, DownloadSupervisor

if TYPE_CHECKING:
    from piperch.repositories import DownloadRepository
    from piperch.services.downloads import ArtworkDownloadService
    from piperch.settings import SettingsManager


@dataclass(frozen=True)
class StubSettingsValue:
    download_concurrency: int


class StubSettings:
    def __init__(self, concurrency: int) -> None:
        self._value = StubSettingsValue(concurrency)

    def get(self) -> StubSettingsValue:
        return self._value


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


class ConcurrentRepository:
    def __init__(self) -> None:
        self.next_item_id = 1
        self.completed = 0

    def recover_interrupted(self) -> None:
        pass

    def claim_next(self) -> tuple[str, DownloadItemRecord] | None:
        if self.next_item_id > 3:
            return None
        item_id = self.next_item_id
        self.next_item_id += 1
        return (
            "job-id",
            DownloadItemRecord(
                item_id=item_id,
                artwork_id=100 + item_id,
                state=ItemState.RUNNING,
                attempts=1,
                error=None,
            ),
        )

    def is_cancel_requested(self, _job_id: str) -> bool:
        return False

    def complete_item(self, _item_id: int, _state: ItemState, _error: str | None = None) -> None:
        self.completed += 1


class ConcurrentDownloadService:
    def __init__(self) -> None:
        self.active = 0
        self.maximum_active = 0
        self.limit_reached = asyncio.Event()
        self.release = asyncio.Event()

    async def download_artwork(
        self,
        _artwork_id: int,
        _job_id: str,
        _is_cancel_requested: object,
    ) -> ItemState:
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        if self.active == 2:
            self.limit_reached.set()
        try:
            await self.release.wait()
            return ItemState.SUCCEEDED
        finally:
            self.active -= 1


@pytest.mark.asyncio
async def test_stop_cancels_an_active_download() -> None:
    repository = BlockingRepository()
    service = BlockingDownloadService()
    supervisor = DownloadSupervisor(
        cast("DownloadRepository", repository),
        cast("ArtworkDownloadService", service),
        DownloadEventBroker(),
        cast("SettingsManager", StubSettings(1)),
    )

    await supervisor.start()
    await asyncio.wait_for(service.started.wait(), timeout=1)
    await asyncio.wait_for(supervisor.stop(), timeout=1)

    assert service.cancelled.is_set()
    await supervisor.stop()


@pytest.mark.asyncio
async def test_supervisor_limits_concurrent_artworks() -> None:
    repository = ConcurrentRepository()
    service = ConcurrentDownloadService()
    supervisor = DownloadSupervisor(
        cast("DownloadRepository", repository),
        cast("ArtworkDownloadService", service),
        DownloadEventBroker(),
        cast("SettingsManager", StubSettings(2)),
    )

    await supervisor.start()
    await asyncio.wait_for(service.limit_reached.wait(), timeout=1)
    assert service.maximum_active == 2
    service.release.set()
    for _ in range(100):
        if repository.completed == 3:
            break
        await asyncio.sleep(0.01)
    await supervisor.stop()

    assert repository.completed == 3
    assert service.maximum_active == 2
