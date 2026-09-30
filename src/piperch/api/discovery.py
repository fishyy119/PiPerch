from __future__ import annotations

from anyio import to_thread
from fastapi import APIRouter, Depends, Path

from piperch.api.dependencies import get_container
from piperch.api.models import (
    ArtworkDiscoveryRequest,
    DiscoveryItem,
    DiscoveryRequest,
    DiscoveryResponse,
    FollowedUserResponse,
    FollowedUsersResponse,
    UserArtworkIdsResponse,
    UserDiscoveryRequest,
)
from piperch.api.pixiv_images import proxied_image_url
from piperch.container import AppContainer

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("", response_model=DiscoveryResponse)
async def discover(
    request: DiscoveryRequest,
    container: AppContainer = Depends(get_container),
) -> DiscoveryResponse:
    settings = await to_thread.run_sync(container.settings.get)
    next_page: int | None = None
    if isinstance(request, ArtworkDiscoveryRequest):
        candidates, next_page = await container.pixiv.discover_artworks(
            request.inputs,
            request.page,
            settings.pixiv_cookie,
        )
    elif isinstance(request, UserDiscoveryRequest):
        candidates, next_page = await container.pixiv.discover_user(
            request.user_id,
            request.page,
            settings.pixiv_cookie,
        )
    else:
        candidates, next_page = await container.pixiv.discover_series(
            request.series_id,
            request.page,
            settings.pixiv_cookie,
        )
    existing_ids = await to_thread.run_sync(
        container.artworks.find_existing_ids,
        [item.artwork_id for item in candidates],
    )
    return DiscoveryResponse(
        items=[
            DiscoveryItem(
                artwork_id=item.artwork_id,
                title=item.title,
                author_name=item.author_name,
                artwork_type=item.artwork_type,
                page_count=item.page_count,
                x_restrict=item.x_restrict,
                is_ai=item.is_ai,
                thumbnail_url=proxied_image_url(item.thumbnail_url),
                in_library=item.artwork_id in existing_ids,
            )
            for item in candidates
        ],
        page=request.page,
        next_page=next_page,
    )


@router.get("/users/{user_id}/selectable-artwork-ids", response_model=UserArtworkIdsResponse)
async def selectable_user_artwork_ids(
    user_id: int = Path(gt=0),
    container: AppContainer = Depends(get_container),
) -> UserArtworkIdsResponse:
    settings = await to_thread.run_sync(container.settings.get)
    artwork_ids = await container.pixiv.list_user_artwork_ids(user_id, settings.pixiv_cookie)
    existing_ids = await to_thread.run_sync(container.artworks.find_existing_ids, artwork_ids)
    return UserArtworkIdsResponse(
        artwork_ids=[artwork_id for artwork_id in artwork_ids if artwork_id not in existing_ids]
    )


@router.get("/followed-users", response_model=FollowedUsersResponse)
async def followed_users(
    container: AppContainer = Depends(get_container),
) -> FollowedUsersResponse:
    settings = await to_thread.run_sync(container.settings.get)
    items = await container.pixiv.list_followed_users(settings.pixiv_cookie)
    return FollowedUsersResponse(
        items=[
            FollowedUserResponse(
                user_id=item.user_id,
                name=item.name,
                avatar_url=proxied_image_url(item.avatar_url),
            )
            for item in items
        ]
    )
