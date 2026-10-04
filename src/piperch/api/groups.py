from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi import Path as PathParameter

from piperch.api.dependencies import get_container
from piperch.api.models import (
    ArtworkGroupResponse,
    ArtworkGroupsRequest,
    ArtworkGroupsResponse,
    BulkArtworkGroupsRequest,
    DeleteResponse,
    GroupNameRequest,
)
from piperch.container import AppContainer

router = APIRouter(tags=["groups"])


@router.get("/groups", response_model=list[ArtworkGroupResponse])
def list_groups(
    container: AppContainer = Depends(get_container),
) -> list[ArtworkGroupResponse]:
    return [
        ArtworkGroupResponse(
            group_id=group.group_id,
            name=group.name,
            artwork_count=group.artwork_count,
        )
        for group in container.groups.list_groups()
    ]


@router.post("/groups", response_model=ArtworkGroupResponse)
def create_group(
    request: GroupNameRequest,
    container: AppContainer = Depends(get_container),
) -> ArtworkGroupResponse:
    group = container.groups.create_group(request.name)
    return ArtworkGroupResponse(
        group_id=group.group_id,
        name=group.name,
        artwork_count=group.artwork_count,
    )


@router.patch("/groups/{group_id}", response_model=ArtworkGroupResponse)
def rename_group(
    request: GroupNameRequest,
    group_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> ArtworkGroupResponse:
    group = container.groups.rename_group(group_id, request.name)
    return ArtworkGroupResponse(
        group_id=group.group_id,
        name=group.name,
        artwork_count=group.artwork_count,
    )


@router.delete("/groups/{group_id}", response_model=DeleteResponse)
def delete_group(
    group_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> DeleteResponse:
    container.groups.delete_group(group_id)
    return DeleteResponse(deleted=1)


@router.put("/artworks/{artwork_id}/groups", response_model=ArtworkGroupsResponse)
def replace_artwork_groups(
    request: ArtworkGroupsRequest,
    artwork_id: int = PathParameter(gt=0),
    container: AppContainer = Depends(get_container),
) -> ArtworkGroupsResponse:
    membership = container.groups.replace_groups(artwork_id, group_ids=request.group_ids)
    return ArtworkGroupsResponse(
        artwork_id=membership.artwork_id,
        group_ids=list(membership.group_ids),
    )


@router.patch("/artworks/groups", status_code=status.HTTP_204_NO_CONTENT)
def bulk_update_artwork_groups(
    request: BulkArtworkGroupsRequest,
    container: AppContainer = Depends(get_container),
) -> Response:
    container.groups.bulk_update_groups(
        request.artwork_ids,
        add_group_ids=request.add_group_ids,
        remove_group_ids=request.remove_group_ids,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
