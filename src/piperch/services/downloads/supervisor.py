from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from anyio import to_thread

from piperch.domain import ItemState
from piperch.errors import AppError
from piperch.services.downloads.artwork import DownloadCancelledError

if TYPE_CHECKING:
    from piperch.repositories import DownloadRepository
    from piperch.services.downloads.artwork import ArtworkDownloadService
    from piperch.services.downloads.events import DownloadEventBroker

logger = logging.getLogger(__name__)


class DownloadSupervisor:
    def __init__(
        self,
        repository: DownloadRepository,
        service: ArtworkDownloadService,
        events: DownloadEventBroker,
    ) -> None:
        self._repository = repository
        self._service = service
        self._events = events
        self._wakeup = asyncio.Event()
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

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

    async def _run(self) -> None:
        while not self._stop.is_set():
            claim = await to_thread.run_sync(self._repository.claim_next)
            if claim is None:
                self._wakeup.clear()
                with suppress(TimeoutError):
                    await asyncio.wait_for(self._wakeup.wait(), timeout=1)
                continue
            job_id, item = claim
            await self._events.publish(job_id)
            try:
                if await to_thread.run_sync(self._repository.is_cancel_requested, job_id):
                    state = ItemState.CANCELLED
                else:

                    async def is_cancel_requested(current_job_id: str = job_id) -> bool:
                        return await to_thread.run_sync(
                            self._repository.is_cancel_requested,
                            current_job_id,
                        )

                    state = await self._service.download_artwork(
                        item.artwork_id,
                        job_id,
                        is_cancel_requested,
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
