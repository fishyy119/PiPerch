from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from piperch.domain import ArtworkType, BookmarkFolderKind, BookmarkVisibility, ItemState, JobState
from piperch.utils.urls import normalize_proxy_url


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ErrorBody(ApiModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class ErrorResponse(ApiModel):
    error: ErrorBody


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    database: Literal["ok"] = "ok"
    instance_id: str


class SettingsResponse(ApiModel):
    pixiv_cookie: str | None
    proxy_url: str | None
    library_root: str
    download_concurrency: int
    request_interval_ms: int
    webp_enabled: bool
    webp_quality: int


class SettingsPatch(ApiModel):
    pixiv_cookie: str | None = None
    proxy_url: str | None = None
    download_concurrency: int = Field(default=3, ge=1, le=8)
    request_interval_ms: int = Field(default=500, ge=0, le=60_000)
    webp_enabled: bool = True
    webp_quality: int = Field(default=85, ge=1, le=100)

    @field_validator("proxy_url")
    @classmethod
    def validate_proxy(cls, value: str | None) -> str | None:
        return normalize_proxy_url(value)

    @model_validator(mode="after")
    def require_change(self) -> SettingsPatch:
        if not self.model_fields_set:
            raise ValueError("至少需要提供一个设置项。")
        return self


class CookieValidationRequest(ApiModel):
    value: str = Field(min_length=1)


class CookieValidationResponse(ApiModel):
    valid: bool


class LibraryMigrationCancelledResponse(ApiModel):
    status: Literal["cancelled"] = "cancelled"
    message: str


class LibraryMigrationStartedResponse(ApiModel):
    status: Literal["started"] = "started"
    message: str
    target_path: str
    instance_id: str


LibraryMigrationResponse = Annotated[
    LibraryMigrationCancelledResponse | LibraryMigrationStartedResponse,
    Field(discriminator="status"),
]


class ArtworkDiscoveryRequest(ApiModel):
    source_type: Literal["artwork"]
    inputs: list[str] = Field(min_length=1, max_length=1000)
    page: int = Field(default=0, ge=0)


class UserDiscoveryRequest(ApiModel):
    source_type: Literal["user"]
    user_id: int = Field(gt=0)
    page: int = Field(default=0, ge=0)


class FollowUpdatesDiscoveryRequest(ApiModel):
    source_type: Literal["followUpdates"]
    page: int = Field(default=0, ge=0)


class SeriesDiscoveryRequest(ApiModel):
    source_type: Literal["series"]
    series_id: int = Field(gt=0)
    page: int = Field(default=0, ge=0)


class BookmarkFolderReference(ApiModel):
    visibility: BookmarkVisibility
    tag: str | None = Field(default=None, max_length=100)


class BookmarkDiscoveryRequest(ApiModel):
    source_type: Literal["bookmark"]
    folder: BookmarkFolderReference
    page: int = Field(default=0, ge=0)


DiscoveryRequest = Annotated[
    ArtworkDiscoveryRequest
    | UserDiscoveryRequest
    | FollowUpdatesDiscoveryRequest
    | SeriesDiscoveryRequest
    | BookmarkDiscoveryRequest,
    Field(discriminator="source_type"),
]


class DiscoveryItem(ApiModel):
    artwork_id: int
    title: str
    author_name: str
    artwork_type: ArtworkType
    page_count: int
    x_restrict: int
    is_ai: bool
    thumbnail_url: str | None
    in_library: bool


class DiscoveryResponse(ApiModel):
    items: list[DiscoveryItem]
    page: int
    next_page: int | None


class RecommendationsResponse(ApiModel):
    items: list[DiscoveryItem]


class RecommendedUserResponse(ApiModel):
    user_id: int
    name: str
    comment: str
    avatar_url: str | None
    is_followed: bool
    artworks: list[DiscoveryItem]


class RecommendedUsersResponse(ApiModel):
    items: list[RecommendedUserResponse]


class UserProfileResponse(ApiModel):
    avatar_url: str | None
    is_followed: bool | None


class ArtworkPreviewResponse(ApiModel):
    urls: list[str]


class UserArtworkIdsResponse(ApiModel):
    artwork_ids: list[int]


class BookmarkFolderResponse(BookmarkFolderReference):
    kind: BookmarkFolderKind
    name: str
    item_count: int


class BookmarkFoldersResponse(ApiModel):
    items: list[BookmarkFolderResponse]


class BookmarkArtworkIdsRequest(ApiModel):
    folders: list[BookmarkFolderReference] = Field(min_length=1, max_length=1000)

    @field_validator("folders")
    @classmethod
    def deduplicate_folders(
        cls,
        folders: list[BookmarkFolderReference],
    ) -> list[BookmarkFolderReference]:
        unique: dict[tuple[BookmarkVisibility, str | None], BookmarkFolderReference] = {}
        for folder in folders:
            unique.setdefault((folder.visibility, folder.tag), folder)
        return list(unique.values())


class FollowedUserResponse(ApiModel):
    user_id: int
    name: str
    avatar_url: str | None


class FollowedUsersResponse(ApiModel):
    items: list[FollowedUserResponse]


class DownloadJobCreate(ApiModel):
    artwork_ids: list[int] = Field(min_length=1, max_length=1000)
    source_label: str = Field(default="手动选择", min_length=1, max_length=200)

    @field_validator("artwork_ids")
    @classmethod
    def validate_artwork_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("作品 ID 必须是正整数。")
        return list(dict.fromkeys(values))


class DownloadJobCreated(ApiModel):
    job_id: str


class DownloadItemResponse(ApiModel):
    item_id: int
    artwork_id: int
    state: ItemState
    attempts: int
    error: str | None


class JobCounts(ApiModel):
    queued: int = 0
    running: int = 0
    skipped: int = 0
    succeeded: int = 0
    failed: int = 0
    cancelled: int = 0


class DownloadJobSummaryResponse(ApiModel):
    job_id: str
    source_label: str
    state: JobState
    created_at: str
    started_at: str | None
    finished_at: str | None
    error_summary: str | None
    counts: JobCounts


class DownloadJobDetailResponse(DownloadJobSummaryResponse):
    items: list[DownloadItemResponse]


class DownloadJobPage(ApiModel):
    items: list[DownloadJobSummaryResponse]
    page: int
    size: int
    total_elements: int
    total_pages: int


class TagResponse(ApiModel):
    tag_id: int
    name: str
    artwork_count: int | None = None


class ArtworkSummaryResponse(ApiModel):
    artwork_id: int
    title: str
    artwork_type: ArtworkType
    author_id: int
    author_name: str
    series_id: int | None
    series_title: str | None
    page_count: int
    x_restrict: int
    is_ai: bool
    published_at: str | None
    downloaded_at: str
    is_favorite: bool
    group_ids: list[int]


class ArtworkPage(ApiModel):
    items: list[ArtworkSummaryResponse]
    page: int
    size: int
    total_elements: int
    total_pages: int


class MediaResponse(ApiModel):
    role: str
    page_index: int | None
    mime_type: str
    byte_size: int


class UgoiraFrameResponse(ApiModel):
    file_name: str
    delay_ms: int


class ArtworkDetailResponse(ArtworkSummaryResponse):
    description: str
    local_linked_artwork_ids: list[int]
    width: int | None
    height: int | None
    tags: list[TagResponse]
    media: list[MediaResponse]
    ugoira_frames: list[UgoiraFrameResponse]


class NamedCountResponse(ApiModel):
    item_id: int
    name: str
    count: int
    subtitle: str | None


class NamedCountPage(ApiModel):
    items: list[NamedCountResponse]
    page: int
    size: int
    total_elements: int
    total_pages: int


class BulkDeleteRequest(ApiModel):
    artwork_ids: list[int] = Field(min_length=1, max_length=1000)

    @field_validator("artwork_ids")
    @classmethod
    def validate_artwork_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("作品 ID 必须是正整数。")
        return list(dict.fromkeys(values))


class DeleteResponse(ApiModel):
    deleted: int


class GroupNameRequest(ApiModel):
    name: str = Field(min_length=1, max_length=20)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ArtworkGroupResponse(ApiModel):
    group_id: int
    name: str
    artwork_count: int


class ArtworkGroupsRequest(ApiModel):
    group_ids: list[int] = Field(default_factory=lambda: list[int](), max_length=10)

    @field_validator("group_ids")
    @classmethod
    def validate_group_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("本地分组 ID 必须是正整数。")
        return list(dict.fromkeys(values))


class FavoriteStateRequest(ApiModel):
    is_favorite: bool


class FavoriteStateResponse(ApiModel):
    artwork_id: int
    is_favorite: bool


class FavoriteSyncPlanResponse(ApiModel):
    plan_id: str
    pixiv_favorite_count: int
    local_artwork_count: int
    local_favorite_count: int
    matched_favorite_count: int
    unavailable_locally_count: int
    add_count: int
    remove_count: int


class FavoriteSyncResultResponse(ApiModel):
    added: int
    removed: int


class ArtworkGroupsResponse(ApiModel):
    artwork_id: int
    group_ids: list[int]


class BulkArtworkGroupsRequest(ApiModel):
    artwork_ids: list[int] = Field(min_length=1, max_length=1000)
    add_group_ids: list[int] = Field(default_factory=lambda: list[int](), max_length=10)
    remove_group_ids: list[int] = Field(default_factory=lambda: list[int](), max_length=10)

    @field_validator("artwork_ids", "add_group_ids", "remove_group_ids")
    @classmethod
    def validate_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("ID 必须是正整数。")
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_changes(self) -> BulkArtworkGroupsRequest:
        if not self.add_group_ids and not self.remove_group_ids:
            raise ValueError("至少需要添加或移除一个本地分组。")
        if set(self.add_group_ids) & set(self.remove_group_ids):
            raise ValueError("同一分组不能同时添加和移除。")
        return self
