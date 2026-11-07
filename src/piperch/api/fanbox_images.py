from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response

from piperch.api.dependencies import get_container
from piperch.api.request_tasks import run_until_disconnect
from piperch.application.container import AppContainer

router = APIRouter(prefix="/fanbox-images", tags=["fanbox"])


def proxied_image_url(url: str | None) -> str | None:
    return f"/api/fanbox-images?url={quote(url, safe='')}" if url else None


@router.get("", response_class=Response)
async def get_fanbox_image(
    url: str,
    request: Request,
    container: AppContainer = Depends(get_container),
) -> Response:
    content, media_type = await run_until_disconnect(request, container.fanbox.fetch_thumbnail(url))
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )
