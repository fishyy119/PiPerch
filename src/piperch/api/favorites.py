from __future__ import annotations

from uuid import UUID

from anyio import to_thread
from fastapi import APIRouter, Depends
from fastapi import Path as PathParameter

from piperch.api.dependencies import get_container
from piperch.api.models import (
    FavoriteStateRequest,
    FavoriteStateResponse,
    FavoriteSyncPlanResponse,
    FavoriteSyncResultResponse,
)
from piperch.container import AppContainer
from piperch.domain import BookmarkFolderReference, BookmarkVisibility

router = APIRouter(tags=["favorites"])


@router.post("/favorite-sync-plans", response_model=FavoriteSyncPlanResponse)
async def create_favorite_sync_plan(
    container: AppContainer = Depends(get_container),
) -> FavoriteSyncPlanResponse:
    settings = await to_thread.run_sync(container.settings.get)
    artwork_ids = await container.pixiv.list_bookmark_artwork_ids(
        [
            BookmarkFolderReference(BookmarkVisibility.PUBLIC, None),
            BookmarkFolderReference(BookmarkVisibility.PRIVATE, None),
        ],
        settings.pixiv_cookie,
    )
    plan = await to_thread.run_sync(lambda: container.favorite_sync.create_plan(artwork_ids))
    diff = plan.diff
    return FavoriteSyncPlanResponse(
        plan_id=str(plan.plan_id),
        pixiv_favorite_count=diff.pixiv_favorite_count,
        local_artwork_count=diff.local_artwork_count,
        local_favorite_count=diff.local_favorite_count,
        matched_favorite_count=diff.matched_favorite_count,
        unavailable_locally_count=diff.unavailable_locally_count,
        add_count=len(diff.add_artwork_ids),
        remove_count=len(diff.remove_artwork_ids),
    )


@router.post(
    "/favorite-sync-plans/{plan_id}/apply",
    response_model=FavoriteSyncResultResponse,
)
async def apply_favorite_sync_plan(
    plan_id: UUID = PathParameter(),
    container: AppContainer = Depends(get_container),
) -> FavoriteSyncResultResponse:
    result = await to_thread.run_sync(lambda: container.favorite_sync.apply_plan(plan_id))
    return FavoriteSyncResultResponse(added=result.added, removed=result.removed)


@router.put("/artworks/{artwork_id}/favorite", response_model=FavoriteStateResponse)
async def replace_favorite_state(
    request: FavoriteStateRequest,
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FavoriteStateResponse:
    await to_thread.run_sync(container.favorites.get_state, artwork_id)
    settings = await to_thread.run_sync(container.settings.get)
    await container.pixiv.sync_bookmark_state(
        artwork_id,
        request.is_favorite,
        settings.pixiv_cookie,
    )
    state = await to_thread.run_sync(
        lambda: container.favorites.replace_state(
            artwork_id,
            is_favorite=request.is_favorite,
        )
    )
    return FavoriteStateResponse(
        artwork_id=state.artwork_id,
        is_favorite=state.is_favorite,
    )
