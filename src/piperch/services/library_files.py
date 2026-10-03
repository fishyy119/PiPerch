from __future__ import annotations

import shutil
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path

LIBRARY_WORKSPACE_NAME = ".piperch-staging"


@dataclass(slots=True)
class PublishedArtworkDirectory:
    """记录已发布的作品目录，并集中处理数据库提交前后的文件收尾。"""

    final_dir: Path
    backup: Path | None

    def rollback(self) -> None:
        if self.final_dir.exists():
            shutil.rmtree(self.final_dir)
        if self.backup is not None and self.backup.exists():
            self.backup.replace(self.final_dir)

    def finalize(self) -> None:
        if self.backup is not None:
            shutil.rmtree(self.backup, ignore_errors=True)


class LibraryFileOperations:
    """管理必须与图库位于同一文件系统的暂存、发布和删除操作。"""

    @staticmethod
    def workspace(library_root: Path) -> Path:
        return library_root.resolve() / LIBRARY_WORKSPACE_NAME

    def download_stage(self, library_root: Path, job_id: str, artwork_id: int) -> Path:
        return self.workspace(library_root) / "download" / job_id / str(artwork_id)

    def delete_root(self, library_root: Path) -> Path:
        return self.workspace(library_root) / "delete"

    def delete_target(self, library_root: Path, author_id: int, artwork_id: int) -> Path:
        return self.delete_root(library_root) / str(author_id) / f"{artwork_id}-{uuid4().hex}"

    @staticmethod
    def publish(stage: Path, final_dir: Path) -> PublishedArtworkDirectory:
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        backup: Path | None = None
        if final_dir.exists():
            backup = final_dir.with_name(f".{final_dir.name}.backup-{uuid4().hex}")
            final_dir.replace(backup)
        try:
            stage.replace(final_dir)
        except Exception:
            if backup is not None:
                backup.replace(final_dir)
            raise
        return PublishedArtworkDirectory(final_dir, backup)

    def cleanup_download_stage(self, library_root: Path, stage: Path) -> None:
        shutil.rmtree(stage, ignore_errors=True)
        self._prune_empty_parents(stage.parent, self.workspace(library_root))

    def cleanup_delete_root(self, library_root: Path) -> None:
        pending_root = self.delete_root(library_root)
        if pending_root.is_dir():
            for child in pending_root.iterdir():
                if child.is_dir():
                    with suppress(OSError):
                        child.rmdir()
        elif not pending_root.exists():
            self._prune_empty_parents(self.workspace(library_root), self.workspace(library_root))
            return
        self._prune_empty_parents(pending_root, self.workspace(library_root))

    @staticmethod
    def _prune_empty_parents(start: Path, boundary: Path) -> None:
        current = start
        while current == boundary or boundary in current.parents:
            try:
                current.rmdir()
            except OSError:
                return
            if current == boundary:
                return
            current = current.parent
