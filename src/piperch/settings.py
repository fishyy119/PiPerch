from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from piperch.domain import AppSettings
from piperch.errors import ConflictError
from piperch.utils.urls import normalize_proxy_url, redact_url_password

_SETTINGS_OBJECT = TypeAdapter(dict[str, object])


class StoredSettings(BaseModel):
    """设置文件的完整持久化结构。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pixiv_cookie: str | None = None
    proxy_url: str | None = None
    library_root: Path
    download_concurrency: int = Field(default=3, ge=1, le=8, strict=True)
    request_interval_ms: int = Field(default=500, ge=0, le=60_000, strict=True)
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

    @field_validator("library_root", mode="before")
    @classmethod
    def normalize_library_root(cls, value: object) -> Path:
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ValueError("图库根目录不能为空。")
        return Path(value).expanduser().resolve()


class SettingsManager:
    def __init__(self, path: Path, default_library: Path) -> None:
        self._path = path
        self._default_library = default_library.expanduser().resolve()
        self._lock = RLock()
        self._current: StoredSettings | None = None

    def initialize(self) -> None:
        """加载设置，并将缺失的文件或字段以默认值补全后写回。"""
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            defaults = StoredSettings(library_root=self._default_library)
            if not self._path.is_file():
                self._save(defaults)
                self._current = defaults
                return

            raw = _SETTINGS_OBJECT.validate_json(self._path.read_text(encoding="utf-8"))

            values = defaults.model_dump(mode="python")
            values.update(raw)
            current = StoredSettings.model_validate(values)
            if raw != current.model_dump(mode="json"):
                self._save(current)
            self._current = current

    def get(self) -> AppSettings:
        with self._lock:
            return self._to_domain(self._require_current())

    def patch(self, **changes: object) -> AppSettings:
        with self._lock:
            current = self._require_current()
            unexpected = changes.keys() - StoredSettings.model_fields.keys()
            if unexpected:
                names = ", ".join(sorted(unexpected))
                raise ValueError(f"Unknown settings: {names}")
            if "proxy_url" in changes and changes["proxy_url"] == redact_url_password(current.proxy_url):
                changes["proxy_url"] = current.proxy_url
            if "library_root" in changes:
                raise ConflictError(
                    "library_migration_required",
                    "请使用图库迁移功能修改图库根目录。",
                )

            updated = StoredSettings.model_validate({**current.model_dump(mode="python"), **changes})
            updated.library_root.mkdir(parents=True, exist_ok=True)
            self._save(updated)
            self._current = updated
            return self._to_domain(updated)

    def set_library_root_after_migration(self, library_root: Path) -> AppSettings:
        """仅在迁移文件校验完成后切换图库根目录。"""
        with self._lock:
            current = self._require_current()
            updated = StoredSettings.model_validate({**current.model_dump(mode="python"), "library_root": library_root})
            if not updated.library_root.is_dir():
                raise ValueError("迁移后的图库根目录不存在。")
            self._save(updated)
            self._current = updated
            return self._to_domain(updated)

    def _save(self, settings: StoredSettings) -> None:
        temporary = self._path.with_suffix(f"{self._path.suffix}.tmp")
        try:
            temporary.write_text(
                json.dumps(settings.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._path)
        finally:
            temporary.unlink(missing_ok=True)

    def _require_current(self) -> StoredSettings:
        if self._current is None:
            raise RuntimeError("设置管理器尚未初始化。")
        return self._current

    @staticmethod
    def _to_domain(settings: StoredSettings) -> AppSettings:
        return AppSettings(
            pixiv_cookie=settings.pixiv_cookie,
            proxy_url=settings.proxy_url,
            library_root=settings.library_root,
            download_concurrency=settings.download_concurrency,
            request_interval_ms=settings.request_interval_ms,
            webp_enabled=settings.webp_enabled,
            webp_quality=settings.webp_quality,
        )
