from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from anyio import to_thread
from fastapi import APIRouter, Depends, Request, Response

from piperch.api.dependencies import get_container
from piperch.api.request_tasks import run_until_disconnect
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
    content, media_type = await run_until_disconnect(request, _fetch_image(url, container))

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


async def _fetch_image(url: str, container: AppContainer) -> tuple[bytes, str]:
    settings = await to_thread.run_sync(container.settings.get)
    return await container.pixiv.fetch_thumbnail(url, settings.pixiv_cookie)
