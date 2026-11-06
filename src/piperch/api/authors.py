from __future__ import annotations

from anyio import to_thread
from fastapi import APIRouter, Depends, Path, Query, Request, Response, status

from piperch.api.dependencies import get_container
from piperch.api.models import (
    FollowedUserResponse,
    FollowedUsersResponse,
    UserProfileResponse,
)
from piperch.api.pixiv_images import proxied_image_url
from piperch.api.request_tasks import run_until_disconnect
from piperch.application.container import AppContainer

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/followed", response_model=FollowedUsersResponse)
async def followed_authors(
    refresh: bool = Query(default=False),
    container: AppContainer = Depends(get_container),
) -> FollowedUsersResponse:
    settings = await to_thread.run_sync(container.settings.get)
    items = await container.pixiv.list_followed_users(settings.pixiv_cookie, refresh=refresh)
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


@router.get("/{author_id}/profile", response_model=UserProfileResponse)
async def author_profile(
    request: Request,
    author_id: int = Path(gt=0),
    container: AppContainer = Depends(get_container),
) -> UserProfileResponse:
    settings = await to_thread.run_sync(container.settings.get)
    profile = await run_until_disconnect(request, container.pixiv.get_user_profile(author_id, settings.pixiv_cookie))
    return UserProfileResponse(
        avatar_url=proxied_image_url(profile.avatar_url),
        is_followed=profile.is_followed,
    )


@router.post("/{author_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_author(
    author_id: int = Path(gt=0),
    container: AppContainer = Depends(get_container),
) -> Response:
    settings = await to_thread.run_sync(container.settings.get)
    await container.pixiv.follow_user(author_id, settings.pixiv_cookie)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{author_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_author(
    author_id: int = Path(gt=0),
    container: AppContainer = Depends(get_container),
) -> Response:
    settings = await to_thread.run_sync(container.settings.get)
    await container.pixiv.unfollow_user(author_id, settings.pixiv_cookie)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
