from __future__ import annotations

from collections.abc import Sequence

from anyio import to_thread
from fastapi import APIRouter, Depends, Path, Query, Request

from piperch.api.dependencies import get_container
from piperch.api.fanbox_images import proxied_image_url as fanbox_image_url
from piperch.api.models import (
    ArtworkDiscoveryFailureResponse,
    ArtworkDiscoveryRequest,
    ArtworkPreviewResponse,
    AuthorResponse,
    AuthorsResponse,
    BookmarkArtworkIdsRequest,
    BookmarkDiscoveryRequest,
    BookmarkFolderResponse,
    BookmarkFoldersResponse,
    DiscoveryItem,
    DiscoveryRequest,
    DiscoveryResponse,
    FollowUpdatesDiscoveryRequest,
    RecommendationsResponse,
    RecommendedUserResponse,
    RecommendedUsersResponse,
    SearchDiscoveryRequest,
    UserArtworkIdsResponse,
    UserDiscoveryRequest,
)
from piperch.api.pixiv_images import proxied_image_url
from piperch.api.request_tasks import run_until_disconnect
from piperch.application.container import AppContainer
from piperch.domain.bookmarks import BookmarkFolderReference
from piperch.domain.discovery import DiscoveryCandidate
from piperch.domain.sources import ArtworkSource
from piperch.errors import AppError

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _discovery_items(
    candidates: Sequence[DiscoveryCandidate],
    existing_ids: dict[int, int],
    source: ArtworkSource = ArtworkSource.PIXIV,
) -> list[DiscoveryItem]:
    return [
        DiscoveryItem(
            artwork_id=item.artwork_id,
            source=source,
            author_id=item.author_id,
            title=item.title,
            author_name=item.author_name,
            artwork_type=item.artwork_type,
            page_count=item.page_count,
            x_restrict=item.x_restrict,
            is_ai=item.is_ai,
            thumbnail_url=(fanbox_image_url if source is ArtworkSource.FANBOX else proxied_image_url)(
                item.thumbnail_url
            ),
            in_library=item.artwork_id in existing_ids,
            preview_only=item.preview_only,
            local_artwork_id=existing_ids.get(item.artwork_id),
        )
        for item in candidates
    ]


@router.post("", response_model=DiscoveryResponse)
async def discover(
    request: DiscoveryRequest,
    container: AppContainer = Depends(get_container),
) -> DiscoveryResponse:
    settings = await to_thread.run_sync(container.settings.get)
    if isinstance(request, ArtworkDiscoveryRequest):
        result = await container.pixiv.discover_artworks(
            request.inputs,
            request.page,
            settings.pixiv_cookie,
        )
    elif isinstance(request, SearchDiscoveryRequest):
        result = await container.pixiv.discover_search(
            request.keyword,
            request.page,
            settings.pixiv_cookie,
        )
    elif isinstance(request, UserDiscoveryRequest):
        if request.source is ArtworkSource.FANBOX:
            result = await container.fanbox.discover_user(request.user_id, request.page)
        else:
            result = await container.pixiv.discover_user(request.user_id, request.page, settings.pixiv_cookie)
    elif isinstance(request, BookmarkDiscoveryRequest):
        result = await container.pixiv.discover_bookmarks(
            BookmarkFolderReference(request.folder.visibility, request.folder.tag),
            request.page,
            settings.pixiv_cookie,
        )
    elif isinstance(request, FollowUpdatesDiscoveryRequest):
        result = await container.pixiv.discover_follow_updates(
            request.page,
            settings.pixiv_cookie,
        )
    else:
        result = await container.pixiv.discover_series(
            request.series_id,
            request.page,
            settings.pixiv_cookie,
        )
    source = request.source if isinstance(request, UserDiscoveryRequest) else ArtworkSource.PIXIV
    existing_ids = await to_thread.run_sync(
        container.artworks.find_local_ids,
        [item.artwork_id for item in result.candidates],
        source,
    )
    return DiscoveryResponse(
        items=_discovery_items(result.candidates, existing_ids, source),
        page=request.page,
        next_page=result.next_page,
        total_pages=result.total_pages,
        failures=[
            ArtworkDiscoveryFailureResponse(artwork_id=item.artwork_id, message=item.message)
            for item in result.failures
        ],
    )


@router.get("/recommendations", response_model=RecommendationsResponse)
async def recommendations(
    container: AppContainer = Depends(get_container),
) -> RecommendationsResponse:
    settings = await to_thread.run_sync(container.settings.get)
    candidates = await container.pixiv.discover_recommended_artworks(settings.pixiv_cookie)
    existing_ids = await to_thread.run_sync(
        container.artworks.find_local_ids,
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
        container.artworks.find_local_ids,
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
    "/artworks/{artwork_id}/recommendations",
    response_model=RecommendationsResponse,
)
async def artwork_recommendations(
    request: Request,
    artwork_id: int = Path(gt=0),
    container: AppContainer = Depends(get_container),
) -> RecommendationsResponse:
    settings = await to_thread.run_sync(container.settings.get)
    candidates = await run_until_disconnect(
        request, container.pixiv.discover_artwork_recommendations(artwork_id, settings.pixiv_cookie)
    )
    existing_ids = await to_thread.run_sync(
        container.artworks.find_local_ids,
        [item.artwork_id for item in candidates],
    )
    return RecommendationsResponse(items=_discovery_items(candidates, existing_ids))


@router.get(
    "/artworks/{artwork_id}/preview",
    response_model=ArtworkPreviewResponse,
)
async def artwork_preview(
    artwork_id: int = Path(gt=0),
    source: ArtworkSource = Query(default=ArtworkSource.PIXIV),
    author_id: int | None = Query(default=None, alias="authorId", gt=0),
    container: AppContainer = Depends(get_container),
) -> ArtworkPreviewResponse:
    if source is ArtworkSource.FANBOX:
        if author_id is None:
            raise AppError("fanbox_author_required", "FANBOX 预览需要作者 ID。", 400)
        urls = await container.fanbox.list_artwork_preview_urls(author_id, artwork_id)
        return ArtworkPreviewResponse(urls=[url for item in urls if (url := fanbox_image_url(item)) is not None])
    settings = await to_thread.run_sync(container.settings.get)
    urls = await container.pixiv.list_artwork_preview_urls(
        artwork_id,
        settings.pixiv_cookie,
    )
    return ArtworkPreviewResponse(urls=[url for item in urls if (url := proxied_image_url(item)) is not None])


@router.get("/fanbox/authors", response_model=AuthorsResponse)
async def search_fanbox_authors(
    request: Request,
    query: str = Query(min_length=1, max_length=100),
    container: AppContainer = Depends(get_container),
) -> AuthorsResponse:
    query = query.strip()
    if not query:
        raise AppError("invalid_author_query", "请输入作者名称。", 400)
    users = await run_until_disconnect(request, container.fanbox.search_creators(query))
    return AuthorsResponse(
        items=[
            AuthorResponse(
                user_id=user.user_id,
                name=user.name,
                avatar_url=proxied_image_url(user.avatar_url),
            )
            for user in users
        ]
    )


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
    source: ArtworkSource = Query(default=ArtworkSource.PIXIV),
    container: AppContainer = Depends(get_container),
) -> UserArtworkIdsResponse:
    if source is ArtworkSource.FANBOX:
        artwork_ids = await container.fanbox.list_user_artwork_ids(user_id)
        existing_ids = await to_thread.run_sync(container.artworks.find_existing_ids, artwork_ids, source)
    else:
        settings = await to_thread.run_sync(container.settings.get)
        artwork_ids = await container.pixiv.list_user_artwork_ids(user_id, settings.pixiv_cookie)
        existing_ids = await to_thread.run_sync(container.artworks.find_existing_ids, artwork_ids)
    return UserArtworkIdsResponse(
        artwork_ids=[artwork_id for artwork_id in artwork_ids if artwork_id not in existing_ids]
    )
