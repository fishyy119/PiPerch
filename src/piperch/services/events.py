from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Sequence


@dataclass(frozen=True, slots=True)
class ServerEvent:
    name: Literal["job-updated", "library-added", "library-removed"]
    data: dict[str, str | list[int]]


class AppEventBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[ServerEvent]] = set()
        try:
            self._loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    async def publish_job_update(self, job_id: str) -> None:
        self._publish(ServerEvent("job-updated", {"jobId": job_id}))

    def publish_library_change(self, artwork_ids: Sequence[int], *, in_library: bool) -> None:
        """在提交锁内按顺序入队，允许数据库工作线程安全发布。"""
        unique_ids = list(dict.fromkeys(artwork_ids))
        if unique_ids and self._loop is not None:
            name = "library-added" if in_library else "library-removed"
            self._loop.call_soon_threadsafe(self._publish, ServerEvent(name, {"artworkIds": unique_ids}))

    def _publish(self, event: ServerEvent) -> None:
        for queue in tuple(self._subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[asyncio.Queue[ServerEvent]]:
        self._loop = asyncio.get_running_loop()
        queue: asyncio.Queue[ServerEvent] = asyncio.Queue(maxsize=32)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)
