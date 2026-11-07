"""在途请求、代理切换与关闭共用的 HTTP 客户端生命周期。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    import httpx


class HttpClientLifecycle:
    def __init__(self, factory: Callable[[str | None], httpx.AsyncClient], proxy_url: str | None) -> None:
        self._factory = factory
        self._client = factory(proxy_url)
        self._proxy_url = proxy_url
        self._condition = asyncio.Condition()
        self._change_lock = asyncio.Lock()
        self._active = 0
        self._switching = False
        self._closed = False

    @asynccontextmanager
    async def use(self) -> AsyncGenerator[httpx.AsyncClient]:
        async with self._condition:
            await self._condition.wait_for(lambda: not self._switching)
            if self._closed:
                raise RuntimeError("HTTP 客户端已关闭。")
            self._active += 1
            client = self._client
        try:
            yield client
        finally:
            async with self._condition:
                self._active -= 1
                self._condition.notify_all()

    async def reconfigure(self, proxy_url: str | None) -> None:
        async with self._change_lock:
            if proxy_url == self._proxy_url:
                return
            async with self._condition:
                self._switching = True
                try:
                    await self._condition.wait_for(lambda: self._active == 0)
                    # 等待完成后才创建替代客户端，取消等待不会遗留未关闭的实例。
                    replacement = self._factory(proxy_url)
                    previous = self._client
                    self._client = replacement
                    self._proxy_url = proxy_url
                finally:
                    self._switching = False
                    self._condition.notify_all()
            await previous.aclose()

    async def close(self) -> None:
        async with self._change_lock:
            async with self._condition:
                self._switching = True
                try:
                    await self._condition.wait_for(lambda: self._active == 0)
                    self._closed = True
                finally:
                    self._switching = False
                    self._condition.notify_all()
            await self._client.aclose()
