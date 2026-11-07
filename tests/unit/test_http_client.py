from __future__ import annotations

import asyncio

import httpx
import pytest

from piperch.utils.http_client import HttpClientLifecycle


@pytest.mark.asyncio
async def test_cancelled_proxy_change_keeps_requests_usable_and_releases_clients() -> None:
    clients: list[httpx.AsyncClient] = []

    def build(proxy_url: str | None) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, text=proxy_url or "direct"),
            )
        )
        clients.append(client)
        return client

    lifecycle = HttpClientLifecycle(build, None)
    try:
        async with asyncio.timeout(2):
            async with lifecycle.use() as original:
                cancelled = asyncio.create_task(lifecycle.reconfigure("http://proxy.test:8080"))
                await asyncio.sleep(0)
                cancelled.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await cancelled
                async with lifecycle.use() as retained:
                    assert (await retained.get("https://media.test/image")).text == "direct"

                switching = asyncio.create_task(lifecycle.reconfigure("http://proxy.test:8080"))
                await asyncio.sleep(0)
                assert (await original.get("https://media.test/image")).text == "direct"
            await switching

            async with lifecycle.use() as replacement:
                assert (await replacement.get("https://media.test/image")).text == "http://proxy.test:8080"
                closing = asyncio.create_task(lifecycle.close())
                await asyncio.sleep(0)
                assert (await replacement.get("https://media.test/image")).status_code == 200
            await closing
            assert all(client.is_closed for client in clients)
    finally:
        await asyncio.wait_for(lifecycle.close(), timeout=2)
