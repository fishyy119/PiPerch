from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from piperch.domain import ArtworkType, ItemState, JobState
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


class SettingsResponse(ApiModel):
    pixiv_cookie: str | None
    proxy_url: str | None
    library_root: str
    download_concurrency: int
    request_interval_ms: int
    webp_enabled: bool
    webp_quality: int


class SettingsUpdate(ApiModel):
    pixiv_cookie: str | None
    proxy_url: str | None = None
    library_root: str = Field(min_length=1)
    download_concurrency: int = Field(ge=1, le=8)
    request_interval_ms: int = Field(ge=0, le=60_000)
    webp_enabled: bool
    webp_quality: int = Field(ge=1, le=100)

    @field_validator("proxy_url")
    @classmethod
    def validate_proxy(cls, value: str | None) -> str | None:
        return normalize_proxy_url(value)


class CookieValidationRequest(ApiModel):
    value: str = Field(min_length=1)


class CookieValidationResponse(ApiModel):
    valid: bool


class ArtworkDiscoveryRequest(ApiModel):
    source_type: Literal["artwork"]
    inputs: list[str] = Field(min_length=1, max_length=1000)
    page: int = Field(default=0, ge=0)


class UserDiscoveryRequest(ApiModel):
    source_type: Literal["user"]
    user_id: int = Field(gt=0)
    page: int = Field(default=0, ge=0)


class SeriesDiscoveryRequest(ApiModel):
    source_type: Literal["series"]
    series_id: int = Field(gt=0)
    page: int = Field(default=0, ge=0)


DiscoveryRequest = Annotated[
    ArtworkDiscoveryRequest | UserDiscoveryRequest | SeriesDiscoveryRequest,
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


class UserArtworkIdsResponse(ApiModel):
    artwork_ids: list[int]


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
    translated_name: str | None
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
