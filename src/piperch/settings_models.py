from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from piperch.utils.urls import normalize_proxy_url


class EditableSettings(BaseModel):
    """可编辑设置的字段、默认值与校验规则，供完整设置和局部更新共用。"""

    model_config = ConfigDict(extra="forbid")

    pixiv_cookie: str | None = None  # TODO: 便捷获取
    proxy_url: str | None = None
    download_concurrency: int = Field(default=3, ge=1, le=8, strict=True)
    request_interval_ms: int = Field(default=500, ge=0, le=60_000, strict=True)
    auto_bookmark_on_download: bool = Field(default=True, strict=True)
    webp_enabled: bool = Field(default=True, strict=True)
    webp_quality: int = Field(default=85, ge=1, le=100, strict=True)

    @field_validator("pixiv_cookie")
    @classmethod
    def normalize_cookie(cls, value: str | None) -> str | None:
        normalized = value.strip() if value else None
        return normalized or None

    @field_validator("proxy_url")
    @classmethod
    def validate_proxy(cls, value: str | None) -> str | None:
        return normalize_proxy_url(value)


class AppSettings(EditableSettings):
    """设置文件的完整持久化结构，同时作为业务代码读取的不可变快照。"""

    model_config = ConfigDict(frozen=True)

    library_root: Path

    @field_validator("library_root", mode="before")
    @classmethod
    def normalize_library_root(cls, value: object) -> Path:
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ValueError("图库根目录不能为空。")
        return Path(value).expanduser().resolve()
