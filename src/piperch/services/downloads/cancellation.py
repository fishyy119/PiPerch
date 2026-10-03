from __future__ import annotations

import asyncio


class DownloadCancelledError(Exception):
    """任务取消后中断尚未提交的作品下载。"""


class DownloadCancellation:
    """在作品下载的安全边界之间传递取消请求。"""

    def __init__(self) -> None:
        self._requested = asyncio.Event()

    @property
    def requested(self) -> bool:
        return self._requested.is_set()

    def request(self) -> None:
        self._requested.set()

    async def wait(self) -> None:
        await self._requested.wait()

    def raise_if_requested(self) -> None:
        if self.requested:
            raise DownloadCancelledError
