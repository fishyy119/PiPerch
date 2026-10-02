from __future__ import annotations

from collections.abc import Sequence

from anyio import to_thread
from fastapi import APIRouter, Depends, Path

from piperch.api.dependencies import get_container
from piperch.api.models import (
    ArtworkDiscoveryRequest,
    ArtworkPreviewResponse,
    BookmarkArtworkIdsRequest,
    BookmarkDiscoveryRequest,
    BookmarkFolderResponse,
    BookmarkFoldersResponse,
    DiscoveryItem,
    DiscoveryRequest,
    DiscoveryResponse,
    RecommendationsResponse,
    RecommendedUserResponse,
    RecommendedUsersResponse,
    UserArtworkIdsResponse,
    UserDiscoveryRequest,
)
from piperch.api.pixiv_images import proxied_image_url
from piperch.container import AppContainer
from piperch.domain import BookmarkFolderReference, DiscoveryCandidate

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _discovery_items(
    candidates: Sequence[DiscoveryCandidate],
    existing_ids: set[int],
) -> list[DiscoveryItem]:
    return [
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
    ]


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
    elif isinstance(request, BookmarkDiscoveryRequest):
        candidates, next_page = await container.pixiv.discover_bookmarks(
            BookmarkFolderReference(request.folder.visibility, request.folder.tag),
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
        items=_discovery_items(candidates, existing_ids),
        page=request.page,
        next_page=next_page,
    )


@router.get("/recommendations", response_model=RecommendationsResponse)
async def recommendations(
    container: AppContainer = Depends(get_container),
) -> RecommendationsResponse:
    settings = await to_thread.run_sync(container.settings.get)
    candidates = await container.pixiv.discover_recommended_artworks(settings.pixiv_cookie)
    existing_ids = await to_thread.run_sync(
        container.artworks.find_existing_ids,
        [item.artwork_id for item in candidates],
    )
    return RecommendationsResponse(items=_discovery_items(candidates, existing_ids))


@router.get("/recommended-users", response_model=RecommendedUsersResponse)
async def recommended_users(
    container: AppContainer = Depends(get_container),
) -> RecommendedUsersResponse:
    settings = await to_thread.run_sync(container.settings.get)
    users = await container.pixiv.discover_recommended_users(settings.pixiv_cookie)
    existing_ids = await to_thread.run_sync(
        container.artworks.find_existing_ids,
        [artwork.artwork_id for user in users for artwork in user.artworks],
    )
    return RecommendedUsersResponse(
        items=[
            RecommendedUserResponse(
                user_id=user.user_id,
                name=user.name,
                comment=user.comment,
                avatar_url=proxied_image_url(user.avatar_url),
                is_followed=user.is_followed,
                artworks=_discovery_items(user.artworks, existing_ids),
            )
            for user in users
        ]
    )


@router.get(
    "/artworks/{artwork_id}/preview",
    response_model=ArtworkPreviewResponse,
)
async def artwork_preview(
    artwork_id: int = Path(gt=0),
    container: AppContainer = Depends(get_container),
) -> ArtworkPreviewResponse:
    settings = await to_thread.run_sync(container.settings.get)
    urls = await container.pixiv.list_artwork_preview_urls(
        artwork_id,
        settings.pixiv_cookie,
    )
    return ArtworkPreviewResponse(urls=[url for item in urls if (url := proxied_image_url(item)) is not None])


@router.get("/bookmark-folders", response_model=BookmarkFoldersResponse)
async def bookmark_folders(
    container: AppContainer = Depends(get_container),
) -> BookmarkFoldersResponse:
    settings = await to_thread.run_sync(container.settings.get)
    folders = await container.pixiv.list_bookmark_folders(settings.pixiv_cookie)
    return BookmarkFoldersResponse(
        items=[
            BookmarkFolderResponse(
                visibility=folder.reference.visibility,
                tag=folder.reference.tag,
                kind=folder.kind,
                name=folder.name,
                item_count=folder.item_count,
            )
            for folder in folders
        ]
    )


@router.post("/bookmarks/selectable-artwork-ids", response_model=UserArtworkIdsResponse)
async def selectable_bookmark_artwork_ids(
    request: BookmarkArtworkIdsRequest,
    container: AppContainer = Depends(get_container),
) -> UserArtworkIdsResponse:
    settings = await to_thread.run_sync(container.settings.get)
    artwork_ids = await container.pixiv.list_bookmark_artwork_ids(
        [BookmarkFolderReference(folder.visibility, folder.tag) for folder in request.folders],
        settings.pixiv_cookie,
    )
    existing_ids = await to_thread.run_sync(container.artworks.find_existing_ids, artwork_ids)
    return UserArtworkIdsResponse(
        artwork_ids=[artwork_id for artwork_id in artwork_ids if artwork_id not in existing_ids]
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
