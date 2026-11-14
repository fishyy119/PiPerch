from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from piperch.domain.artworks import ArtworkType
from piperch.domain.bookmarks import BookmarkFolderKind, BookmarkVisibility
from piperch.domain.downloads import ItemState, JobState
from piperch.domain.groups import MAX_ARTWORK_GROUPS, MAX_GROUP_NAME_LENGTH
from piperch.domain.sources import ArtworkSource
from piperch.settings.models import EditableSettings


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


_API_MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


ArtworkIdList = Annotated[list[int], Field(min_length=1, max_length=1000)]
GroupIdList = Annotated[list[int], Field(max_length=MAX_ARTWORK_GROUPS)]


def _normalize_ids(values: list[int], *, label: str = "ID") -> list[int]:
    if any(value <= 0 for value in values):
        raise ValueError(f"{label} 必须是正整数。")
    return list(dict.fromkeys(values))


class ApiModel(BaseModel):
    model_config = _API_MODEL_CONFIG


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
    auto_bookmark_on_download: bool
    webp_enabled: bool
    webp_quality: int


class SettingsPatch(EditableSettings):
    """仅提交显式提供的字段，共用的默认值不参与局部更新。"""

    model_config: ClassVar[ConfigDict] = {**_API_MODEL_CONFIG, **EditableSettings.model_config}

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


class SearchDiscoveryRequest(ApiModel):
    source_type: Literal["search"]
    keyword: str = Field(min_length=1)
    page: int = Field(default=0, ge=0)

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        keyword = value.strip()
        if not keyword:
            raise ValueError("请输入搜索内容。")
        return keyword


class UserDiscoveryRequest(ApiModel):
    source_type: Literal["user"]
    source: ArtworkSource = ArtworkSource.PIXIV
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
    | SearchDiscoveryRequest
    | UserDiscoveryRequest
    | FollowUpdatesDiscoveryRequest
    | SeriesDiscoveryRequest
    | BookmarkDiscoveryRequest,
    Field(discriminator="source_type"),
]


class DiscoveryItem(ApiModel):
    artwork_id: int
    source: ArtworkSource = ArtworkSource.PIXIV
    local_artwork_id: int | None = None
    title: str
    author_name: str
    author_id: int | None = None
    artwork_type: ArtworkType
    page_count: int
    x_restrict: int | None
    is_ai: bool | None
    thumbnail_url: str | None
    in_library: bool
    preview_only: bool = False


class ArtworkDiscoveryFailureResponse(ApiModel):
    artwork_id: int
    message: str


class DiscoveryResponse(ApiModel):
    items: list[DiscoveryItem]
    page: int
    next_page: int | None
    total_pages: int | None = None
    failures: list[ArtworkDiscoveryFailureResponse] = Field(
        default_factory=lambda: list[ArtworkDiscoveryFailureResponse]()
    )


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


class AuthorResponse(ApiModel):
    user_id: int
    name: str
    avatar_url: str | None


class AuthorsResponse(ApiModel):
    items: list[AuthorResponse]


class DownloadJobCreate(ApiModel):
    artwork_ids: ArtworkIdList
    source: ArtworkSource = ArtworkSource.PIXIV
    source_label: str = Field(default="手动选择", min_length=1, max_length=200)
    author_ids: dict[Annotated[int, Field(gt=0)], Annotated[int, Field(gt=0)]] = Field(
        default_factory=lambda: dict[int, int](), max_length=1000
    )

    @field_validator("artwork_ids")
    @classmethod
    def validate_artwork_ids(cls, values: list[int]) -> list[int]:
        return _normalize_ids(values, label="作品 ID")

    @model_validator(mode="after")
    def require_fanbox_authors(self) -> DownloadJobCreate:
        if self.source is ArtworkSource.FANBOX and any(
            artwork_id not in self.author_ids for artwork_id in self.artwork_ids
        ):
            raise ValueError("FANBOX 下载必须同时提供每篇投稿的作者 ID。")
        return self


class DownloadJobCreated(ApiModel):
    job_id: str


class DownloadItemResponse(ApiModel):
    item_id: int
    source: ArtworkSource
    remote_id: int
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


class ArtworkGroupRecordResponse(ApiModel):
    group_id: int
    name: str


class ArtworkSummaryResponse(ApiModel):
    artwork_id: int
    source: ArtworkSource
    remote_id: int
    title: str
    artwork_type: ArtworkType
    author_id: int
    author_name: str
    series_id: int | None
    series_title: str | None
    page_count: int
    x_restrict: int | None
    is_ai: bool | None
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


class ArtworkImageResponse(ApiModel):
    artwork_id: int
    role: Literal["page", "ugoira"]
    page_index: int | None
    width: int | None
    height: int | None


class UgoiraFrameResponse(ApiModel):
    file_name: str
    delay_ms: int


class ArtworkDetailResponse(ArtworkSummaryResponse):
    description: str
    local_linked_artworks: dict[str, int]
    tags: list[TagResponse]
    groups: list[ArtworkGroupRecordResponse]
    images: list[ArtworkImageResponse]
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
    artwork_ids: ArtworkIdList

    @field_validator("artwork_ids")
    @classmethod
    def validate_artwork_ids(cls, values: list[int]) -> list[int]:
        return _normalize_ids(values, label="作品 ID")


class DeleteResponse(ApiModel):
    deleted: int


class ArtworkDeleteResponse(DeleteResponse):
    skipped_favorite_artwork_ids: list[int]


class GroupNameRequest(ApiModel):
    name: str = Field(min_length=1, max_length=MAX_GROUP_NAME_LENGTH)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ArtworkGroupResponse(ArtworkGroupRecordResponse):
    artwork_count: int


class ArtworkGroupsRequest(ApiModel):
    group_ids: GroupIdList = Field(default_factory=lambda: list[int]())

    @field_validator("group_ids")
    @classmethod
    def validate_group_ids(cls, values: list[int]) -> list[int]:
        return _normalize_ids(values, label="本地分组 ID")


class FavoriteStateRequest(ApiModel):
    is_favorite: bool


class FavoriteStateResponse(ApiModel):
    artwork_id: int
    is_favorite: bool
    pixiv_synced: bool


class FavoriteSyncPlanResponse(ApiModel):
    plan_id: str
    pixiv_favorite_count: int
    local_artwork_count: int
    local_favorite_count: int
    matched_favorite_count: int
    unavailable_locally_count: int
    add_count: int
    remove_count: int
    preserved_favorite_count: int


class FavoriteSyncResultResponse(ApiModel):
    added: int
    removed: int


class ArtworkGroupsResponse(ApiModel):
    artwork_id: int
    group_ids: list[int]


class BulkArtworkGroupsRequest(ApiModel):
    artwork_ids: ArtworkIdList
    add_group_ids: GroupIdList = Field(default_factory=lambda: list[int]())
    remove_group_ids: GroupIdList = Field(default_factory=lambda: list[int]())

    @field_validator("artwork_ids", "add_group_ids", "remove_group_ids")
    @classmethod
    def validate_ids(cls, values: list[int]) -> list[int]:
        return _normalize_ids(values)

    @model_validator(mode="after")
    def validate_changes(self) -> BulkArtworkGroupsRequest:
        if not self.add_group_ids and not self.remove_group_ids:
            raise ValueError("至少需要添加或移除一个本地分组。")
        if set(self.add_group_ids) & set(self.remove_group_ids):
            raise ValueError("同一分组不能同时添加和移除。")
        return self
