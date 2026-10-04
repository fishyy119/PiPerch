from __future__ import annotations

import math
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi import Path as PathParameter
from fastapi.responses import FileResponse
from pydantic import Field

from piperch.api.converters import artwork_detail_response, artwork_summary_response
from piperch.api.dependencies import get_container
from piperch.api.models import (
    ArtworkDetailResponse,
    ArtworkPage,
    ArtworkSummaryResponse,
    BulkDeleteRequest,
    DeleteResponse,
    NamedCountPage,
    NamedCountResponse,
    TagResponse,
)
from piperch.container import AppContainer
from piperch.domain import ArtworkType
from piperch.errors import NotFoundError

router = APIRouter(tags=["gallery"])
PositiveId = Annotated[int, Field(gt=0)]


@router.get("/artworks", response_model=ArtworkPage)
def list_artworks(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=24, ge=1, le=100),
    search: str = Query(default="", max_length=200),
    tag_id: list[PositiveId] = Query(default=[], alias="tagId"),
    author_id: int | None = Query(default=None, gt=0, alias="authorId"),
    series_id: int | None = Query(default=None, gt=0, alias="seriesId"),
    artwork_type: ArtworkType | None = Query(default=None, alias="artworkType"),
    rating: str = Query(default="all", pattern="^(all|safe|r18)$"),
    ai: str = Query(default="all", pattern="^(all|yes|no)$"),
    favorite: str = Query(default="all", pattern="^(all|yes|no)$"),
    group_id: list[PositiveId] = Query(default=[], alias="groupId"),
    sort: str = Query(default="downloadedAt", pattern="^(downloadedAt|publishedAt|title|id|random)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    random_seed: int = Query(default=0, ge=0, lt=2_147_483_647, alias="randomSeed"),
    container: AppContainer = Depends(get_container),
) -> ArtworkPage:
    items, total = container.artworks.list_artworks(
        page=page,
        size=size,
        search=search,
        tag_ids=tag_id,
        author_id=author_id,
        series_id=series_id,
        artwork_type=artwork_type,
        rating=rating,
        ai=ai,
        favorite=favorite,
        group_ids=group_id,
        sort=sort,
        order=order,
        random_seed=random_seed,
    )
    return ArtworkPage(
        items=[artwork_summary_response(item) for item in items],
        page=page,
        size=size,
        total_elements=total,
        total_pages=math.ceil(total / size),
    )


@router.get("/artworks/{artwork_id}", response_model=ArtworkDetailResponse)
def get_artwork(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> ArtworkDetailResponse:
    return artwork_detail_response(container.artworks.get_detail(artwork_id))


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
    return FileResponse(_safe_media_path(root, media.relative_path), media_type=media.mime_type)


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
    return FileResponse(thumbnail, media_type="image/webp")


@router.get("/artworks/{artwork_id}/ugoira", response_class=FileResponse)
def get_ugoira(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FileResponse:
    media = container.artworks.get_media(artwork_id, "ugoiraZip", None)
    root = container.settings.get().library_root
    return FileResponse(
        _safe_media_path(root, media.relative_path),
        media_type="application/zip",
        filename=Path(media.relative_path).name,
    )


@router.get("/artworks/{artwork_id}/cover", response_class=FileResponse)
def get_ugoira_cover(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> FileResponse:
    media = container.artworks.get_media(artwork_id, "cover", None)
    root = container.settings.get().library_root
    return FileResponse(_safe_media_path(root, media.relative_path), media_type=media.mime_type)


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
    return FileResponse(thumbnail, media_type="image/webp")


@router.delete("/artworks/{artwork_id}", response_model=DeleteResponse)
def delete_artwork(
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> DeleteResponse:
    container.storage.require_available()
    return DeleteResponse(deleted=container.library.delete_artworks([artwork_id]))


@router.post("/artworks/bulk-delete", response_model=DeleteResponse)
def bulk_delete_artworks(
    request: BulkDeleteRequest,
    container: AppContainer = Depends(get_container),
) -> DeleteResponse:
    container.storage.require_available()
    return DeleteResponse(deleted=container.library.delete_artworks(request.artwork_ids))


@router.get("/tags", response_model=list[TagResponse])
def list_tags(
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    include_id: list[PositiveId] = Query(default=[], alias="includeId"),
    container: AppContainer = Depends(get_container),
) -> list[TagResponse]:
    return [
        TagResponse(
            tag_id=tag_id,
            name=tag.name,
            translated_name=tag.translated_name,
            artwork_count=count,
        )
        for tag_id, tag, count in container.artworks.list_tags(search, limit, include_id)
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
            item_id=item.item_id,
            name=item.name,
            count=item.count,
            subtitle=item.subtitle,
        )
        for item in container.artworks.list_authors(search, limit, include_id)
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
                item_id=item.item_id,
                name=item.name,
                count=item.count,
                subtitle=item.subtitle,
            )
            for item in items
        ],
        page=page,
        size=size,
        total_elements=total,
        total_pages=math.ceil(total / size),
    )
