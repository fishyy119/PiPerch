from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING
from uuid import uuid4

from anyio import to_thread
from pydantic import BaseModel, ConfigDict

from piperch.errors import AppError, ConflictError

if TYPE_CHECKING:
    from piperch.paths import AppPaths
    from piperch.repositories import DownloadRepository
    from piperch.runtime import AppControl
    from piperch.services.downloads import DownloadSupervisor
    from piperch.settings import SettingsManager

logger = logging.getLogger(__name__)

_MIGRATION_MARKER = ".piperch-migration"


class StorageMigrationJournal(BaseModel):
    """用于判断中断迁移应回滚还是继续清理的最小持久化状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    source: Path
    target: Path
    staging: Path


@dataclass(frozen=True, slots=True)
class StorageMigrationSelection:
    target: Path


@dataclass(frozen=True, slots=True)
class _LibraryManifest:
    directories: tuple[Path, ...]
    files: dict[Path, int]

    @property
    def total_bytes(self) -> int:
        return sum(self.files.values())


class StorageMigrationService:
    def __init__(
        self,
        paths: AppPaths,
        settings: SettingsManager,
        downloads: DownloadRepository,
        supervisor: DownloadSupervisor,
        control: AppControl,
        mutation_lock: Lock,
    ) -> None:
        self._paths = paths
        self._settings = settings
        self._downloads = downloads
        self._supervisor = supervisor
        self._control = control
        self._mutation_lock = mutation_lock
        self._operation_lock = Lock()

    def require_available(self) -> None:
        if self._operation_lock.locked():
            raise ConflictError("library_migration_in_progress", "图库目录正在选择或迁移中，请稍后再试。")

    def prepare_interactive(self) -> StorageMigrationSelection | None:
        if not self._operation_lock.acquire(blocking=False):
            raise ConflictError("library_migration_in_progress", "图库目录正在选择或迁移中，请稍后再试。")
        keep_lock = False
        try:
            if self._paths.storage_migration.exists():
                raise ConflictError(
                    "library_migration_recovery_pending",
                    "上一次图库迁移仍有内容待恢复或清理，请查看后端日志。",
                )
            source = self._settings.get().library_root.resolve()
            target = self._select_and_confirm(source)
            if target is None:
                return None
            keep_lock = True
            return StorageMigrationSelection(target=target)
        finally:
            if not keep_lock:
                self._operation_lock.release()

    async def migrate(self, target: Path) -> None:
        restart_required = False
        try:
            source = self._settings.get().library_root.resolve()
            logger.info("开始迁移图库: %s -> %s", source, target)
            restart_required = True
            logger.info("正在停止下载监督器。")
            await self._supervisor.stop()
            jobs, items = await to_thread.run_sync(self._downloads.cancel_active)
            logger.info("已取消 %d 个下载任务、%d 个未完成下载项。", jobs, items)
            await to_thread.run_sync(self._migrate_files, source, target)
            logger.info("图库迁移成功: %s -> %s", source, target)
        except Exception:
            logger.exception("图库迁移失败。")
        finally:
            self._operation_lock.release()
            if restart_required:
                logger.info("图库迁移流程结束，正在重启后端服务。")
                self._control.request_restart()

    def recover(self) -> None:
        journal = self._load_journal()
        if journal is None:
            return
        try:
            self._validate_journal_paths(journal)
            current = self._settings.get().library_root.resolve()
            source = journal.source.resolve()
            target = journal.target.resolve()
            if current == source:
                logger.warning("发现未完成的图库迁移，正在回滚目标目录。")
                self._remove_staging(journal)
                if target.is_dir() and self._has_marker(target, journal.token):
                    shutil.rmtree(target)
                    target.mkdir(parents=True)
                elif not target.exists():
                    target.mkdir(parents=True)
                self._clear_journal()
                return
            if current == target:
                logger.warning("发现待清理的旧图库目录，正在继续清理。")
                self._remove_marker(target, journal.token)
                if source.exists():
                    shutil.rmtree(source)
                self._remove_staging(journal)
                self._clear_journal()
                return
            logger.error("迁移日志与当前图库目录不一致，已保留现场供人工检查。")
        except Exception:
            logger.exception("恢复中断的图库迁移失败，已保留迁移日志供下次启动重试。")

    def _select_and_confirm(self, source: Path) -> Path | None:
        try:
            import tkinter
            from tkinter import filedialog, messagebox
        except ImportError as error:
            raise AppError(
                "directory_picker_unavailable",
                "当前 Python 环境不包含 Tkinter，无法打开目录选择器。",
                503,
            ) from error

        root: tkinter.Tk | None = None
        try:
            root = tkinter.Tk()
            root.withdraw()
            root.attributes("-topmost", True)  # pyright: ignore[reportUnknownMemberType]
            root.update_idletasks()
            selected = filedialog.askdirectory(
                parent=root,
                title="选择新的图库目录",
                initialdir=str(source),
                mustexist=True,
            )
            if not selected:
                return None
            target = Path(selected).expanduser().resolve(strict=True)
            self._validate_target(source, target, probe=True)
            job_count, item_count = self._downloads.count_active()
            confirmed = messagebox.askokcancel(
                "确认迁移图库",
                (
                    f"当前目录:\n{source}\n\n"
                    f"目标目录:\n{target}\n\n"
                    f"将取消 {job_count} 个下载任务中的 {item_count} 个未完成项目。\n"
                    "迁移期间请勿关闭程序，完成后后端会自动重启。"
                ),
                parent=root,
                icon="warning",
            )
            return target if confirmed else None
        except tkinter.TclError as error:
            raise AppError(
                "directory_picker_unavailable",
                "无法打开系统目录选择器，请确认当前会话支持桌面窗口。",
                503,
            ) from error
        finally:
            if root is not None:
                root.destroy()

    def _migrate_files(self, source: Path, target: Path) -> None:
        with self._mutation_lock:
            self._validate_target(source, target, probe=False)
            manifest = self._scan(source)
            logger.info(
                "图库扫描完成: %d 个文件，共 %d 字节。",
                len(manifest.files),
                manifest.total_bytes,
            )
            token = uuid4().hex
            staging = target.with_name(f".{target.name}.piperch-migration-{token}")
            journal = StorageMigrationJournal(
                token=token,
                source=source,
                target=target,
                staging=staging,
            )
            self._validate_journal_paths(journal)
            self._save_journal(journal)
            switched = False
            try:
                logger.info("正在复制图库文件。")
                self._copy_manifest(source, staging, manifest, token)
                copied = self._scan(staging, ignored={Path(_MIGRATION_MARKER)})
                if copied.files != manifest.files or set(copied.directories) != set(manifest.directories):
                    raise OSError("迁移后的文件清单与源目录不一致。")
                logger.info("图库文件复制和校验完成。")
                target.rmdir()
                staging.replace(target)
                self._settings.set_library_root_after_migration(target)
                switched = True
                self._remove_marker(target, token)
                logger.info("图库根目录已切换为 %s。", target)
                try:
                    shutil.rmtree(source)
                except OSError:
                    logger.exception("旧图库目录暂时无法删除，将在重启后继续清理: %s", source)
                else:
                    self._clear_journal()
                    logger.info("旧图库目录已删除，迁移完成。")
            except Exception:
                if switched:
                    logger.exception("图库已切换，但后续清理失败，将在重启后继续处理。")
                    return
                self._rollback_copy(journal)
                raise

    def _validate_target(self, source: Path, target: Path, *, probe: bool) -> None:
        source = source.resolve()
        target = target.resolve()
        if not source.is_dir():
            raise AppError("library_source_unavailable", "当前图库目录不存在或不是目录。", 409)
        if source.parent == source:
            raise AppError("library_source_unsafe", "图库根目录不能是磁盘根目录。", 409)
        if not target.is_dir():
            raise AppError("library_target_unavailable", "目标路径不存在或不是目录。", 409)
        if target.parent == target:
            raise AppError("library_target_unsafe", "不能直接使用磁盘根目录作为目标目录。", 409)
        if source == target:
            raise AppError("library_target_same", "目标目录与当前图库目录相同。", 409)
        if source in target.parents or target in source.parents:
            raise AppError("library_target_nested", "当前目录和目标目录不能互相嵌套。", 409)
        try:
            if next(target.iterdir(), None) is not None:
                raise AppError("library_target_not_empty", "目标目录必须为空。", 409)
            if probe:
                probe_path = target.parent / f".{target.name}.piperch-probe-{uuid4().hex}"
                probe_path.mkdir()
                probe_path.rmdir()
        except AppError:
            raise
        except OSError as error:
            raise AppError("library_target_unavailable", "目标目录不可写或无法访问。", 409) from error

    @staticmethod
    def _scan(root: Path, *, ignored: set[Path] | None = None) -> _LibraryManifest:
        ignored = ignored or set()
        directories: list[Path] = []
        files: dict[Path, int] = {}
        pending = [root]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    relative = path.relative_to(root)
                    if relative in ignored:
                        continue
                    is_junction = getattr(path, "is_junction", lambda: False)()
                    if entry.is_symlink() or is_junction:
                        raise OSError(f"图库中包含不支持迁移的链接: {relative}")
                    if entry.is_dir(follow_symlinks=False):
                        directories.append(relative)
                        pending.append(path)
                    elif entry.is_file(follow_symlinks=False):
                        files[relative] = entry.stat(follow_symlinks=False).st_size
                    else:
                        raise OSError(f"图库中包含不支持迁移的特殊文件: {relative}")
        return _LibraryManifest(tuple(sorted(directories)), files)

    @staticmethod
    def _copy_manifest(
        source: Path,
        staging: Path,
        manifest: _LibraryManifest,
        token: str,
    ) -> None:
        staging.mkdir()
        (staging / _MIGRATION_MARKER).write_text(token, encoding="utf-8")
        for relative in manifest.directories:
            (staging / relative).mkdir()
        for relative in manifest.files:
            shutil.copy2(source / relative, staging / relative)
        for relative in reversed(manifest.directories):
            shutil.copystat(source / relative, staging / relative)
        shutil.copystat(source, staging)

    def _rollback_copy(self, journal: StorageMigrationJournal) -> None:
        self._remove_staging(journal)
        target = journal.target.resolve()
        if target.is_dir() and self._has_marker(target, journal.token):
            shutil.rmtree(target)
            target.mkdir(parents=True)
        elif not target.exists():
            target.mkdir(parents=True)
        self._clear_journal()

    def _remove_staging(self, journal: StorageMigrationJournal) -> None:
        staging = journal.staging.resolve()
        if not staging.exists():
            return
        expected_name = f".{journal.target.name}.piperch-migration-{journal.token}"
        if staging.parent != journal.target.resolve().parent or staging.name != expected_name:
            raise OSError("迁移临时目录不符合安全清理规则。")
        shutil.rmtree(staging)

    @staticmethod
    def _has_marker(root: Path, token: str) -> bool:
        marker = root / _MIGRATION_MARKER
        try:
            return marker.is_file() and marker.read_text(encoding="utf-8") == token
        except OSError:
            return False

    @staticmethod
    def _remove_marker(root: Path, token: str) -> None:
        marker = root / _MIGRATION_MARKER
        if marker.exists() and marker.read_text(encoding="utf-8") != token:
            raise OSError("迁移标记与当前操作不匹配。")
        marker.unlink(missing_ok=True)

    @staticmethod
    def _validate_journal_paths(journal: StorageMigrationJournal) -> None:
        source = journal.source.resolve()
        target = journal.target.resolve()
        staging = journal.staging.resolve()
        if source.parent == source or target.parent == target:
            raise OSError("迁移日志包含不安全的磁盘根目录。")
        if source == target or source in target.parents or target in source.parents:
            raise OSError("迁移日志包含互相嵌套的目录。")
        expected_name = f".{target.name}.piperch-migration-{journal.token}"
        if staging.parent != target.parent or staging.name != expected_name:
            raise OSError("迁移日志包含不安全的临时目录。")

    def _load_journal(self) -> StorageMigrationJournal | None:
        if not self._paths.storage_migration.is_file():
            return None
        return StorageMigrationJournal.model_validate_json(self._paths.storage_migration.read_text(encoding="utf-8"))

    def _save_journal(self, journal: StorageMigrationJournal) -> None:
        temporary = self._paths.storage_migration.with_suffix(".json.tmp")
        try:
            temporary.write_text(
                json.dumps(journal.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._paths.storage_migration)
        finally:
            temporary.unlink(missing_ok=True)

    def _clear_journal(self) -> None:
        self._paths.storage_migration.unlink(missing_ok=True)
