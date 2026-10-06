from __future__ import annotations

import shutil
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING

from piperch.errors import AppError, NotFoundError
from piperch.services.library_files import LibraryFileOperations
from piperch.services.thumbnails import ArtworkThumbnailCache

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from piperch.paths import AppPaths
    from piperch.repositories import ArtworkRepository
    from piperch.settings import SettingsManager


@dataclass(frozen=True, slots=True)
class ArtworkDeleteResult:
    deleted: int
    skipped_favorite_artwork_ids: tuple[int, ...]


class LibraryService:
    def __init__(
        self,
        paths: AppPaths,
        settings: SettingsManager,
        artworks: ArtworkRepository,
        thumbnails: ArtworkThumbnailCache | None = None,
        mutation_lock: Lock | None = None,
        files: LibraryFileOperations | None = None,
    ) -> None:
        self._paths = paths
        self._settings = settings
        self._artworks = artworks
        self._thumbnails = thumbnails or ArtworkThumbnailCache(paths)
        self._mutation_lock = mutation_lock or Lock()
        self._files = files or LibraryFileOperations()

    def delete_artworks(self, artwork_ids: Sequence[int]) -> ArtworkDeleteResult:
        with self._mutation_lock:
            return self._delete_artworks(artwork_ids)

    def _delete_artworks(self, artwork_ids: Sequence[int]) -> ArtworkDeleteResult:
        root = self._settings.get().library_root.resolve()
        requested_ids = tuple(dict.fromkeys(artwork_ids))
        existing_ids: list[int] = []
        deletable_ids: list[int] = []
        staged: list[tuple[int, Path, Path]] = []
        try:
            for artwork_id in requested_ids:
                try:
                    detail = self._artworks.get_detail(artwork_id)
                except NotFoundError:
                    continue
                existing_ids.append(artwork_id)
                if detail.summary.is_favorite:
                    continue
                deletable_ids.append(artwork_id)
                source = (root / str(detail.summary.author_id) / str(artwork_id)).resolve()
                self._require_safe_artwork_path(root, source)
                if source.exists():
                    if not source.is_dir():
                        raise AppError(
                            "unsafe_delete_path",
                            "作品路径不是目录，已拒绝操作。",
                            409,
                        )
                    target = self._files.delete_target(root, detail.summary.author_id, artwork_id)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source.replace(target)
                    staged.append((artwork_id, source, target))
            deleted_ids = self._artworks.delete_metadata(deletable_ids)
        except Exception:
            for _, source, target in reversed(staged):
                if target.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    target.replace(source)
            self._files.cleanup_delete_root(root)
            raise

        for artwork_id, source, target in staged:
            if artwork_id in deleted_ids:
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                target.replace(source)
        for artwork_id in deleted_ids:
            self._thumbnails.delete_artwork(artwork_id)
        self._files.cleanup_delete_root(root)
        return ArtworkDeleteResult(
            deleted=len(deleted_ids),
            skipped_favorite_artwork_ids=tuple(
                artwork_id for artwork_id in existing_ids if artwork_id not in deleted_ids
            ),
        )

    def recover_pending_deletes(self) -> None:
        """根据数据库是否仍有作品记录，完成或回滚进程中断的删除操作。"""
        library_root = self._settings.get().library_root.resolve()
        legacy_root = self._paths.staging / "delete"
        pending_roots = (legacy_root, self._files.delete_root(library_root))
        for pending_root in dict.fromkeys(pending_roots):
            self._recover_pending_deletes(pending_root, library_root)
        self._files.cleanup_delete_root(library_root)

    def _recover_pending_deletes(self, pending_root: Path, library_root: Path) -> None:
        if not pending_root.is_dir():
            return
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
