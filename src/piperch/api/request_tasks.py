"""将无请求体的只读异步操作绑定到 HTTP 连接，断连时取消。"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from starlette.requests import ClientDisconnect

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from fastapi import Request


async def run_until_disconnect[T](request: Request, operation: Coroutine[object, object, T]) -> T:
    task = asyncio.create_task(operation)
    disconnect = asyncio.create_task(_wait_for_disconnect(request))
    try:
        done, _pending = await asyncio.wait((task, disconnect), return_when=asyncio.FIRST_COMPLETED)
        if disconnect in done:
            await disconnect
            raise ClientDisconnect
        return await task
    finally:
        # 普通响应不会自动中止断连前的上游请求，显式清理操作和断连监听任务。
        task.cancel()
        disconnect.cancel()
        await asyncio.gather(task, disconnect, return_exceptions=True)


async def _wait_for_disconnect(request: Request) -> None:
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return
