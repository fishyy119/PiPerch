from __future__ import annotations

from anyio import to_thread
from fastapi import APIRouter, Depends
from fastapi import Path as PathParameter

from piperch.api.dependencies import get_container
from piperch.api.models import (
    BulkFavoriteGroupsRequest,
    BulkFavoriteRequest,
    DeleteResponse,
    FavoriteGroupNameRequest,
    FavoriteGroupResponse,
    FavoriteStateRequest,
    FavoriteStateResponse,
    FavoriteSyncResponse,
    MutationResponse,
)
from piperch.container import AppContainer
from piperch.domain import FavoriteState

router = APIRouter(tags=["favorites"])


def _state_response(state: FavoriteState) -> FavoriteStateResponse:
    return FavoriteStateResponse(
        artwork_id=state.artwork_id,
        is_favorite=state.is_favorite,
        group_ids=list(state.group_ids),
    )


@router.get("/favorite-groups", response_model=list[FavoriteGroupResponse])
def list_favorite_groups(
    container: AppContainer = Depends(get_container),
) -> list[FavoriteGroupResponse]:
    return [
        FavoriteGroupResponse(
            group_id=group.group_id,
            name=group.name,
            artwork_count=group.artwork_count,
        )
        for group in container.favorites.list_groups()
    ]


@router.post("/favorite-groups", response_model=FavoriteGroupResponse)
def create_favorite_group(
    request: FavoriteGroupNameRequest,
    container: AppContainer = Depends(get_container),
) -> FavoriteGroupResponse:
    group = container.favorites.create_group(request.name)
    return FavoriteGroupResponse(
        group_id=group.group_id,
        name=group.name,
        artwork_count=group.artwork_count,
    )


@router.patch("/favorite-groups/{group_id}", response_model=FavoriteGroupResponse)
def rename_favorite_group(
    request: FavoriteGroupNameRequest,
    group_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FavoriteGroupResponse:
    group = container.favorites.rename_group(group_id, request.name)
    return FavoriteGroupResponse(
        group_id=group.group_id,
        name=group.name,
        artwork_count=group.artwork_count,
    )


@router.delete("/favorite-groups/{group_id}", response_model=DeleteResponse)
def delete_favorite_group(
    group_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> DeleteResponse:
    container.favorites.delete_group(group_id)
    return DeleteResponse(deleted=1)


@router.put("/artworks/{artwork_id}/favorite", response_model=FavoriteStateResponse)
def replace_favorite_state(
    request: FavoriteStateRequest,
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FavoriteStateResponse:
    return _state_response(
        container.favorites.replace_state(
            artwork_id,
            is_favorite=request.is_favorite,
            group_ids=request.group_ids,
        )
    )


@router.post("/artworks/bulk-favorite", response_model=MutationResponse)
def bulk_set_favorite(
    request: BulkFavoriteRequest,
    container: AppContainer = Depends(get_container),
) -> MutationResponse:
    container.favorites.bulk_set_favorite(request.artwork_ids, is_favorite=request.is_favorite)
    return MutationResponse(updated=len(request.artwork_ids))


@router.post("/artworks/bulk-favorite-groups", response_model=MutationResponse)
def bulk_update_favorite_groups(
    request: BulkFavoriteGroupsRequest,
    container: AppContainer = Depends(get_container),
) -> MutationResponse:
    container.favorites.bulk_update_groups(
        request.artwork_ids,
        add_group_ids=request.add_group_ids,
        remove_group_ids=request.remove_group_ids,
    )
    return MutationResponse(updated=len(request.artwork_ids))


@router.post("/artworks/{artwork_id}/favorite/sync", response_model=FavoriteSyncResponse)
async def sync_favorite(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FavoriteSyncResponse:
    state = await to_thread.run_sync(container.favorites.get_state, artwork_id)
    settings = await to_thread.run_sync(container.settings.get)
    result = await container.pixiv.sync_public_bookmark(
        artwork_id,
        state.group_names if state.is_favorite else None,
        settings.pixiv_cookie,
    )
    return FavoriteSyncResponse(is_favorite=result.is_favorite, tags=list(result.tags))
