from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

from anyio import to_thread

from piperch.domain import DownloadItemRecord, ItemState
from piperch.errors import AppError
from piperch.services.downloads.cancellation import (
    DownloadCancellation,
    DownloadCancelledError,
)

if TYPE_CHECKING:
    from piperch.repositories import DownloadRepository
    from piperch.services.downloads.artwork import ArtworkDownloadService
    from piperch.services.downloads.events import DownloadEventBroker
    from piperch.settings import SettingsManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ActiveDownload:
    job_id: str
    cancellation: DownloadCancellation


class DownloadSupervisor:
    def __init__(
        self,
        repository: DownloadRepository,
        service: ArtworkDownloadService,
        events: DownloadEventBroker,
        settings: SettingsManager,
    ) -> None:
        self._repository = repository
        self._service = service
        self._events = events
        self._settings = settings
        self._wakeup = asyncio.Event()
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._active: dict[asyncio.Task[None], _ActiveDownload] = {}

    async def start(self) -> None:
        await to_thread.run_sync(self._repository.recover_interrupted)
        self._task = asyncio.create_task(self._run(), name="piperch-download-supervisor")
        self._wakeup.set()

    async def stop(self) -> None:
        self._stop.set()
        self._wakeup.set()
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    def notify(self) -> None:
        self._wakeup.set()

    async def request_cancel(self, job_id: str) -> None:
        await to_thread.run_sync(self._repository.request_cancel, job_id)
        for active in self._active.values():
            if active.job_id == job_id:
                active.cancellation.request()
        self._wakeup.set()
        await self._events.publish(job_id)

    async def _run(self) -> None:
        try:
            while not self._stop.is_set():
                self._wakeup.clear()
                concurrency = (await to_thread.run_sync(self._settings.get)).download_concurrency
                while len(self._active) < concurrency and not self._stop.is_set():
                    claim = await to_thread.run_sync(self._repository.claim_next)
                    if claim is None:
                        break
                    job_id, item = claim
                    cancellation = DownloadCancellation()
                    task = asyncio.create_task(
                        self._process_item(job_id, item, cancellation),
                        name=f"piperch-download-{item.item_id}",
                    )
                    self._active[task] = _ActiveDownload(job_id, cancellation)

                if not self._active:
                    with suppress(TimeoutError):
                        await asyncio.wait_for(self._wakeup.wait(), timeout=1)
                    continue

                wakeup = asyncio.create_task(self._wakeup.wait())
                try:
                    done, _pending = await asyncio.wait(
                        {*self._active, wakeup},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                finally:
                    if not wakeup.done():
                        wakeup.cancel()
                        with suppress(asyncio.CancelledError):
                            await wakeup
                completed = [task for task in self._active if task in done]
                for task in completed:
                    self._active.pop(task)
                    task.result()
        finally:
            for task in self._active:
                task.cancel()
            await asyncio.gather(*self._active, return_exceptions=True)
            self._active.clear()

    async def _process_item(
        self,
        job_id: str,
        item: DownloadItemRecord,
        cancellation: DownloadCancellation,
    ) -> None:
        await self._events.publish(job_id)
        try:
            if await to_thread.run_sync(self._repository.is_cancel_requested, job_id):
                cancellation.request()

            if cancellation.requested:
                state = ItemState.CANCELLED
            else:
                state = await self._service.download_artwork(
                    item.artwork_id,
                    job_id,
                    cancellation,
                )
            await to_thread.run_sync(
                self._repository.complete_item,
                item.item_id,
                state,
            )
        except asyncio.CancelledError:
            raise
        except DownloadCancelledError:
            await to_thread.run_sync(
                self._repository.complete_item,
                item.item_id,
                ItemState.CANCELLED,
            )
        except AppError as error:
            await to_thread.run_sync(
                self._repository.complete_item,
                item.item_id,
                ItemState.FAILED,
                error.message,
            )
        except Exception:
            logger.exception("下载作品失败: artwork_id=%s", item.artwork_id)
            await to_thread.run_sync(
                self._repository.complete_item,
                item.item_id,
                ItemState.FAILED,
                "下载过程中发生未预期错误。",
            )
        await self._events.publish(job_id)
