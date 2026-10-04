from __future__ import annotations

from anyio import to_thread
from fastapi import APIRouter, Depends
from fastapi import Path as PathParameter

from piperch.api.dependencies import get_container
from piperch.api.models import FavoriteStateRequest, FavoriteStateResponse
from piperch.container import AppContainer

router = APIRouter(tags=["favorites"])


@router.put("/artworks/{artwork_id}/favorite", response_model=FavoriteStateResponse)
async def replace_favorite_state(
    request: FavoriteStateRequest,
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FavoriteStateResponse:
    state = await to_thread.run_sync(
        lambda: container.favorites.replace_state(
            artwork_id,
            is_favorite=request.is_favorite,
        )
    )
    settings = await to_thread.run_sync(container.settings.get)
    await container.pixiv.sync_bookmark_state(
        artwork_id,
        state.is_favorite,
        settings.pixiv_cookie,
    )
    return FavoriteStateResponse(
        artwork_id=state.artwork_id,
        is_favorite=state.is_favorite,
    )
