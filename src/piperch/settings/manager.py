from __future__ import annotations

import json
from threading import RLock
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from piperch.errors import ConflictError
from piperch.settings.models import AppSettings
from piperch.utils.urls import redact_url_password

if TYPE_CHECKING:
    from pathlib import Path

_SETTINGS_OBJECT = TypeAdapter(dict[str, object])


class SettingsManager:
    def __init__(self, path: Path, default_library: Path) -> None:
        self._path = path
        self._default_library = default_library.expanduser().resolve()
        self._lock = RLock()
        self._current: AppSettings | None = None

    def initialize(self) -> None:
        """加载设置，并将缺失的文件或字段以默认值补全后写回。"""
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            defaults = AppSettings(library_root=self._default_library)
            if not self._path.is_file():
                self._save(defaults)
                self._current = defaults
                return

            raw = _SETTINGS_OBJECT.validate_json(self._path.read_text(encoding="utf-8"))

            values = defaults.model_dump(mode="python")
            values.update(raw)
            current = AppSettings.model_validate(values)
            if raw != current.model_dump(mode="json"):
                self._save(current)
            self._current = current

    def get(self) -> AppSettings:
        with self._lock:
            return self._require_current()

    def patch(self, **changes: object) -> AppSettings:
        with self._lock:
            current = self._require_current()
            unexpected = changes.keys() - AppSettings.model_fields.keys()
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

            updated = AppSettings.model_validate({**current.model_dump(mode="python"), **changes})
            updated.library_root.mkdir(parents=True, exist_ok=True)
            self._save(updated)
            self._current = updated
            return updated

    def set_library_root_after_migration(self, library_root: Path) -> AppSettings:
        """仅在迁移文件校验完成后切换图库根目录。"""
        with self._lock:
            current = self._require_current()
            updated = AppSettings.model_validate({**current.model_dump(mode="python"), "library_root": library_root})
            if not updated.library_root.is_dir():
                raise ValueError("迁移后的图库根目录不存在。")
            self._save(updated)
            self._current = updated
            return updated

    def _save(self, settings: AppSettings) -> None:
        temporary = self._path.with_suffix(f"{self._path.suffix}.tmp")
        try:
            temporary.write_text(
                json.dumps(settings.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._path)
        finally:
            temporary.unlink(missing_ok=True)

    def _require_current(self) -> AppSettings:
        if self._current is None:
            raise RuntimeError("设置管理器尚未初始化。")
        return self._current
