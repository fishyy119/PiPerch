from __future__ import annotations

import asyncio
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from anyio import to_thread
from fastapi import APIRouter, Depends, Request, Response

from piperch.api.dependencies import get_container
from piperch.application.container import AppContainer

router = APIRouter(prefix="/pixiv-images", tags=["pixiv"])


def proxied_image_url(url: str | None) -> str | None:
    if not url:
        return None
    return f"/api/pixiv-images?url={quote(url, safe='')}"


@router.get("", response_class=Response)
async def get_pixiv_image(
    url: str,
    request: Request,
    container: AppContainer = Depends(get_container),
) -> Response:
    download = asyncio.create_task(_fetch_image(url, container))
    disconnect = asyncio.create_task(_wait_for_disconnect(request))
    try:
        done, _pending = await asyncio.wait((download, disconnect), return_when=asyncio.FIRST_COMPLETED)
        if disconnect in done:
            await disconnect
            return Response(status_code=499)
        content, media_type = await download
    finally:
        # 普通响应不会自动中止断连前的上游请求，显式清理下载和断连监听任务。
        download.cancel()
        disconnect.cancel()
        await asyncio.gather(download, disconnect, return_exceptions=True)

    filename = PurePosixPath(unquote(urlsplit(url).path).replace("\\", "/")).name or "image"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename, safe='')}",
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _wait_for_disconnect(request: Request) -> None:
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return


async def _fetch_image(url: str, container: AppContainer) -> tuple[bytes, str]:
    settings = await to_thread.run_sync(container.settings.get)
    return await container.pixiv.fetch_thumbnail(url, settings.pixiv_cookie)
