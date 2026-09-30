from __future__ import annotations

from urllib.parse import quote

from anyio import to_thread
from fastapi import APIRouter, Depends, Response

from piperch.api.dependencies import get_container
from piperch.container import AppContainer

router = APIRouter(prefix="/pixiv-images", tags=["pixiv"])


def proxied_image_url(url: str | None) -> str | None:
    if not url:
        return None
    return f"/api/pixiv-images?url={quote(url, safe='')}"


@router.get("", response_class=Response)
async def get_pixiv_image(
    url: str,
    container: AppContainer = Depends(get_container),
) -> Response:
    settings = await to_thread.run_sync(container.settings.get)
    content, media_type = await container.pixiv.fetch_thumbnail(url, settings.pixiv_cookie)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )
