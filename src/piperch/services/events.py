from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Sequence

    from piperch.domain.sources import ArtworkSource, LibraryArtworkReference


class JobUpdatePayload(TypedDict):
    jobId: str


class LibraryReferencePayload(TypedDict):
    localArtworkId: int
    source: ArtworkSource
    remoteId: int


class LibraryChangePayload(TypedDict):
    references: list[LibraryReferencePayload]


@dataclass(frozen=True, slots=True)
class JobUpdatedEvent:
    name: Literal["job-updated"]
    data: JobUpdatePayload


@dataclass(frozen=True, slots=True)
class LibraryChangedEvent:
    name: Literal["library-added", "library-removed"]
    data: LibraryChangePayload


type ServerEvent = JobUpdatedEvent | LibraryChangedEvent


class AppEventBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[ServerEvent]] = set()
        try:
            self._loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    async def publish_job_update(self, job_id: str) -> None:
        self._publish(JobUpdatedEvent("job-updated", {"jobId": job_id}))

    def publish_library_change(
        self,
        references: Sequence[LibraryArtworkReference],
        *,
        in_library: bool,
    ) -> None:
        """在提交锁内按顺序入队，允许数据库工作线程安全发布。"""
        unique_references = tuple(dict.fromkeys(references))
        if unique_references and self._loop is not None:
            name = "library-added" if in_library else "library-removed"
            self._loop.call_soon_threadsafe(
                self._publish,
                LibraryChangedEvent(
                    name,
                    {
                        "references": [
                            {"localArtworkId": item.local_artwork_id, "source": item.source, "remoteId": item.remote_id}
                            for item in unique_references
                        ],
                    },
                ),
            )

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
