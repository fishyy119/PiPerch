from __future__ import annotations

import shutil
from threading import Lock
from typing import TYPE_CHECKING
from uuid import uuid4

from piperch.errors import AppError, NotFoundError
from piperch.services.thumbnails import ArtworkThumbnailCache

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from piperch.paths import AppPaths
    from piperch.repositories import ArtworkRepository
    from piperch.settings import SettingsManager


class LibraryService:
    def __init__(
        self,
        paths: AppPaths,
        settings: SettingsManager,
        artworks: ArtworkRepository,
        thumbnails: ArtworkThumbnailCache | None = None,
        mutation_lock: Lock | None = None,
    ) -> None:
        self._paths = paths
        self._settings = settings
        self._artworks = artworks
        self._thumbnails = thumbnails or ArtworkThumbnailCache(paths)
        self._mutation_lock = mutation_lock or Lock()

    def delete_artworks(self, artwork_ids: Sequence[int]) -> int:
        with self._mutation_lock:
            return self._delete_artworks(artwork_ids)

    def _delete_artworks(self, artwork_ids: Sequence[int]) -> int:
        root = self._settings.get().library_root.resolve()
        staged: list[tuple[Path, Path]] = []
        try:
            for artwork_id in dict.fromkeys(artwork_ids):
                try:
                    detail = self._artworks.get_detail(artwork_id)
                except NotFoundError:
                    continue
                source = (root / str(detail.summary.author_id) / str(artwork_id)).resolve()
                self._require_safe_artwork_path(root, source)
                if source.exists():
                    if not source.is_dir():
                        raise AppError(
                            "unsafe_delete_path",
                            "作品路径不是目录，已拒绝操作。",
                            409,
                        )
                    target = (
                        self._paths.staging / "delete" / str(detail.summary.author_id) / f"{artwork_id}-{uuid4().hex}"
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source.replace(target)
                    staged.append((source, target))
            deleted = self._artworks.delete_metadata(artwork_ids)
        except Exception:
            for source, target in reversed(staged):
                if target.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    target.replace(source)
            raise
        for _, target in staged:
            shutil.rmtree(target, ignore_errors=True)
        for artwork_id in artwork_ids:
            self._thumbnails.delete_artwork(artwork_id)
        return deleted

    def recover_pending_deletes(self) -> None:
        """根据数据库是否仍有作品记录，完成或回滚进程中断的删除操作。"""
        pending_root = self._paths.staging / "delete"
        if not pending_root.is_dir():
            return
        library_root = self._settings.get().library_root.resolve()
        for author_dir in pending_root.iterdir():
            if not author_dir.is_dir() or not author_dir.name.isdecimal():
                continue
            for target in author_dir.iterdir():
                artwork_text = target.name.split("-", 1)[0]
                if not artwork_text.isdecimal() or not target.is_dir():
                    continue
                artwork_id = int(artwork_text)
                try:
                    self._artworks.get_detail(artwork_id)
                except NotFoundError:
                    shutil.rmtree(target, ignore_errors=True)
                    continue
                source = (library_root / author_dir.name / artwork_text).resolve()
                self._require_safe_artwork_path(library_root, source)
                if source.exists():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    source.parent.mkdir(parents=True, exist_ok=True)
                    target.replace(source)
            if not any(author_dir.iterdir()):
                author_dir.rmdir()
        if not any(pending_root.iterdir()):
            pending_root.rmdir()

    @staticmethod
    def _require_safe_artwork_path(root: Path, source: Path) -> None:
        if source == root or root not in source.parents or len(source.relative_to(root).parts) != 2:
            raise AppError(
                "unsafe_delete_path",
                "作品目录不符合安全删除规则，已拒绝操作。",
                409,
            )
