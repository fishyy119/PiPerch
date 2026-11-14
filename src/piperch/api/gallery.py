from __future__ import annotations

import math
from pathlib import Path
from typing import Annotated, Literal

from anyio import to_thread
from fastapi import APIRouter, Depends, Query
from fastapi import Path as PathParameter
from fastapi.responses import FileResponse
from pydantic import Field

from piperch.api.converters import artwork_detail_response, artwork_image_response, artwork_summary_response
from piperch.api.dependencies import get_container
from piperch.api.models import (
    ArtworkDeleteResponse,
    ArtworkDetailResponse,
    ArtworkImageResponse,
    ArtworkLinkResponse,
    ArtworkPage,
    ArtworkSummaryResponse,
    BulkDeleteRequest,
    NamedCountPage,
    NamedCountResponse,
    RandomArtworkResponse,
    TagResponse,
)
from piperch.application.container import AppContainer
from piperch.domain.artworks import ArtworkType
from piperch.errors import ConflictError, NotFoundError
from piperch.services.artwork_links import parse_artwork_links

router = APIRouter(tags=["gallery"])
PositiveId = Annotated[int, Field(gt=0)]


@router.get("/artworks", response_model=ArtworkPage)
async def list_artworks(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=24, ge=1, le=100),
    search: str = Query(default="", max_length=200),
    tag_id: list[PositiveId] = Query(default=[], alias="tagId"),
    tag_match: Literal["any", "all"] = Query(default="any", alias="tagMatch"),
    author_id: PositiveId | Literal["followed", "unfollowed"] | None = Query(default=None, alias="authorId"),
    series_id: int | None = Query(default=None, gt=0, alias="seriesId"),
    artwork_type: ArtworkType | None = Query(default=None, alias="artworkType"),
    rating: str = Query(default="all", pattern="^(all|safe|r18)$"),
    ai: str = Query(default="all", pattern="^(all|yes|no)$"),
    favorite: str = Query(default="all", pattern="^(all|yes|no)$"),
    group_id: list[PositiveId] = Query(default=[], alias="groupId"),
    group_match: Literal["any", "all"] = Query(default="any", alias="groupMatch"),
    sort: str = Query(default="downloadedAt", pattern="^(downloadedAt|publishedAt|title|id|random)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    random_seed: int = Query(default=0, ge=0, lt=2_147_483_647, alias="randomSeed"),
    container: AppContainer = Depends(get_container),
) -> ArtworkPage:
    followed_author_ids: frozenset[int] = frozenset()
    if isinstance(author_id, str):
        settings = await to_thread.run_sync(container.settings.get)
        followed_users = await container.pixiv.list_followed_users(settings.pixiv_cookie)
        followed_author_ids = frozenset(user.user_id for user in followed_users)

    items, total = await to_thread.run_sync(
        lambda: container.artworks.list_artworks(
            page=page,
            size=size,
            search=search,
            tag_ids=tag_id,
            tag_match=tag_match,
            author_id=author_id,
            series_id=series_id,
            artwork_type=artwork_type,
            rating=rating,
            ai=ai,
            favorite=favorite,
            followed_author_ids=followed_author_ids,
            group_ids=group_id,
            group_match=group_match,
            sort=sort,
            order=order,
            random_seed=random_seed,
        )
    )
    return ArtworkPage(
        items=[artwork_summary_response(item) for item in items],
        page=page,
        size=size,
        total_elements=total,
        total_pages=math.ceil(total / size),
    )


@router.get("/artworks/images", response_model=list[ArtworkImageResponse])
def list_artwork_images(
    artwork_ids: list[PositiveId] = Query(alias="artworkId", min_length=1, max_length=100),
    container: AppContainer = Depends(get_container),
) -> list[ArtworkImageResponse]:
    return [artwork_image_response(image) for image in container.artworks.list_artwork_images(artwork_ids)]


@router.get("/artworks/random", response_model=RandomArtworkResponse)
def get_random_artwork(
    exclude_artwork_id: int | None = Query(default=None, gt=0, alias="excludeArtworkId"),
    container: AppContainer = Depends(get_container),
) -> RandomArtworkResponse:
    return RandomArtworkResponse(artwork_id=container.artworks.get_random_artwork_id(exclude_artwork_id))


@router.get("/artworks/{artwork_id}", response_model=ArtworkDetailResponse)
def get_artwork(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> ArtworkDetailResponse:
    detail = container.artworks.get_detail(artwork_id)
    artwork_links: dict[str, ArtworkLinkResponse] = {}
    for source, links in parse_artwork_links(detail.description).items():
        local_ids = container.artworks.find_local_ids(list(links.values()), source)
        artwork_links.update(
            {
                href: ArtworkLinkResponse(
                    source=source,
                    remote_id=remote_id,
                    local_artwork_id=local_ids.get(remote_id),
                )
                for href, remote_id in links.items()
            }
        )
    return artwork_detail_response(
        detail,
        artwork_links,
        container.artworks.list_artwork_images([artwork_id]),
    )


@router.get("/artworks/{artwork_id}/related", response_model=list[ArtworkSummaryResponse])
def list_related_artworks(
    artwork_id: int = PathParameter(gt=0),
    limit: int = Query(default=12, ge=1, le=50),
    container: AppContainer = Depends(get_container),
) -> list[ArtworkSummaryResponse]:
    return [artwork_summary_response(item) for item in container.artworks.list_related_artworks(artwork_id, limit)]


def _safe_media_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise NotFoundError("本地媒体文件不存在。")
    return path


@router.get("/artworks/{artwork_id}/pages/{page_index}", response_class=FileResponse)
def get_artwork_page(
    artwork_id: int = PathParameter(gt=0),
    page_index: int = PathParameter(ge=0),
    container: AppContainer = Depends(get_container),
) -> FileResponse:
    media = container.artworks.get_media(artwork_id, "page", page_index)
    root = container.settings.get().library_root
    return FileResponse(
        _safe_media_path(root, media.relative_path),
        media_type=media.mime_type,
        filename=Path(media.relative_path).name,
        content_disposition_type="inline",
    )


@router.get("/artworks/{artwork_id}/pages/{page_index}/thumbnail", response_class=FileResponse)
def get_artwork_page_thumbnail(
    artwork_id: int = PathParameter(gt=0),
    page_index: int = PathParameter(ge=0),
    container: AppContainer = Depends(get_container),
) -> FileResponse:
    media = container.artworks.get_media(artwork_id, "page", page_index)
    root = container.settings.get().library_root
    source = _safe_media_path(root, media.relative_path)
    thumbnail = container.thumbnails.ensure_page_thumbnail(artwork_id, page_index, source)
    return FileResponse(
        thumbnail,
        media_type="image/webp",
        filename=f"{artwork_id}_p{page_index}_thumbnail.webp",
        content_disposition_type="inline",
    )


@router.get("/artworks/{artwork_id}/ugoira", response_class=FileResponse)
def get_ugoira(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FileResponse:
    media = container.artworks.get_media(artwork_id, "ugoiraZip", None)
    detail = container.artworks.get_detail(artwork_id)
    settings = container.settings.get()
    animation = container.animations.ensure_animation(
        artwork_id,
        _safe_media_path(settings.library_root, media.relative_path),
        detail.ugoira_frames,
        settings.webp_quality,
    )
    return FileResponse(
        animation,
        media_type="image/webp",
        filename=f"{artwork_id}_ugoira.webp",
        content_disposition_type="inline",
    )


@router.get("/artworks/{artwork_id}/cover", response_class=FileResponse)
def get_ugoira_cover(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FileResponse:
    media = container.artworks.get_media(artwork_id, "cover", None)
    root = container.settings.get().library_root
    return FileResponse(
        _safe_media_path(root, media.relative_path),
        media_type=media.mime_type,
        filename=Path(media.relative_path).name,
        content_disposition_type="inline",
    )


@router.get("/artworks/{artwork_id}/thumbnail", response_class=FileResponse)
def get_thumbnail(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FileResponse:
    detail = container.artworks.get_detail(artwork_id)
    source_record = next((item for item in detail.media if item.role in {"page", "cover"}), None)
    if source_record is None:
        raise NotFoundError("作品没有可用于生成缩略图的媒体文件。")
    root = container.settings.get().library_root
    source = _safe_media_path(root, source_record.relative_path)
    thumbnail = container.thumbnails.ensure_cover_thumbnail(artwork_id, source)
    return FileResponse(
        thumbnail,
        media_type="image/webp",
        filename=f"{artwork_id}_thumbnail.webp",
        content_disposition_type="inline",
    )


@router.delete("/artworks/{artwork_id}", response_model=ArtworkDeleteResponse)
def delete_artwork(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> ArtworkDeleteResponse:
    container.storage.require_available()
    result = container.library.delete_artworks([artwork_id])
    if result.skipped_favorite_artwork_ids:
        raise ConflictError(
            "favorite_artwork_delete_forbidden",
            "收藏作品不可永久删除，请先取消收藏。",
        )
    return ArtworkDeleteResponse(deleted=result.deleted, skipped_favorite_artwork_ids=[])


@router.post("/artworks/bulk-delete", response_model=ArtworkDeleteResponse)
def bulk_delete_artworks(
    request: BulkDeleteRequest,
    container: AppContainer = Depends(get_container),
) -> ArtworkDeleteResponse:
    container.storage.require_available()
    result = container.library.delete_artworks(request.artwork_ids)
    return ArtworkDeleteResponse(
        deleted=result.deleted,
        skipped_favorite_artwork_ids=list(result.skipped_favorite_artwork_ids),
    )


@router.get("/tags", response_model=list[TagResponse])
def list_tags(
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    include_id: list[PositiveId] = Query(default=[], alias="includeId"),
    container: AppContainer = Depends(get_container),
) -> list[TagResponse]:
    return [
        TagResponse(
            tag_id=tag.tag_id,
            name=tag.name,
            artwork_count=tag.artwork_count,
        )
        for tag in container.artworks.list_tags(search, limit, include_id)
    ]


@router.get("/authors", response_model=list[NamedCountResponse])
def list_authors(
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    include_id: list[PositiveId] = Query(default=[], alias="includeId"),
    container: AppContainer = Depends(get_container),
) -> list[NamedCountResponse]:
    return [
        NamedCountResponse(
            item_id=author.author_id,
            name=author.name,
            count=author.artwork_count,
            subtitle=None,
        )
        for author in container.artworks.list_authors(search, limit, include_id)
    ]


@router.get("/series", response_model=NamedCountPage)
def list_series(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=24, ge=1, le=100),
    search: str = Query(default="", max_length=100),
    container: AppContainer = Depends(get_container),
) -> NamedCountPage:
    items, total = container.artworks.list_series(page, size, search)
    return NamedCountPage(
        items=[
            NamedCountResponse(
                item_id=series.series_id,
                name=series.title,
                count=series.artwork_count,
                subtitle=series.author_name,
            )
            for series in items
        ],
        page=page,
        size=size,
        total_elements=total,
        total_pages=math.ceil(total / size),
    )
