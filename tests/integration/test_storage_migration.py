from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

import pytest

from piperch.database import Database, run_migrations
from piperch.domain import JobState
from piperch.paths import AppPaths
from piperch.repositories import DownloadRepository
from piperch.runtime import AppControl
from piperch.services.library_files import LibraryFileOperations
from piperch.services.storage import StorageMigrationJournal, StorageMigrationService
from piperch.settings import SettingsManager

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


class StubSupervisor:
    def __init__(self) -> None:
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


def _storage(
    tmp_path: Path,
) -> tuple[
    AppPaths,
    Database,
    SettingsManager,
    DownloadRepository,
    StubSupervisor,
    list[bool],
    StorageMigrationService,
]:
    paths = AppPaths.from_data_dir(tmp_path / "data")
    paths.ensure_directories()
    run_migrations(paths)
    database = Database(paths.database)
    settings = SettingsManager(paths.settings, paths.default_library)
    settings.initialize()
    settings.get().library_root.mkdir(parents=True)
    downloads = DownloadRepository(database)
    supervisor = StubSupervisor()
    restarted: list[bool] = []
    service = StorageMigrationService(
        paths,
        settings,
        downloads,
        supervisor,  # type: ignore[arg-type]
        AppControl("test-instance", lambda: restarted.append(True)),
        Lock(),
    )
    return paths, database, settings, downloads, supervisor, restarted, service


@pytest.mark.asyncio
async def test_storage_migration_moves_all_files_and_cancels_unfinished_downloads(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    paths, database, settings, downloads, supervisor, restarted, service = _storage(tmp_path)
    source = settings.get().library_root
    target = tmp_path / "moved-library"
    target.mkdir()
    managed = source / "100" / "1" / "1_p0.jpg"
    managed.parent.mkdir(parents=True)
    managed.write_bytes(b"managed")
    (source / "untracked.txt").write_text("untracked", encoding="utf-8")
    workspace = LibraryFileOperations.workspace(source)
    workspace.mkdir()
    (workspace / "interrupted.part").write_bytes(b"temporary")
    job_id = downloads.create_job([1, 2], "迁移测试")

    def select_target(_source: Path) -> Path:
        return target

    monkeypatch.setattr(service, "_select_and_confirm", select_target)
    try:
        selection = service.prepare_interactive()
        assert selection is not None

        await service.migrate(selection.target)

        assert supervisor.stopped
        assert restarted == [True]
        assert settings.get().library_root == target.resolve()
        assert (target / "100" / "1" / "1_p0.jpg").read_bytes() == b"managed"
        assert (target / "untracked.txt").read_text(encoding="utf-8") == "untracked"
        assert not (target / workspace.name).exists()
        assert not source.exists()
        assert downloads.get_job(job_id).state is JobState.CANCELLED
        assert not paths.storage_migration.exists()
    finally:
        database.close()


@pytest.mark.asyncio
async def test_storage_migration_failure_keeps_source_and_setting(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    paths, database, settings, _, supervisor, restarted, service = _storage(tmp_path)
    source = settings.get().library_root
    (source / "keep.txt").write_text("keep", encoding="utf-8")
    target = tmp_path / "failed-target"
    target.mkdir()

    def select_target(_source: Path) -> Path:
        return target

    monkeypatch.setattr(service, "_select_and_confirm", select_target)

    def fail_copy(_source: Path, _target: Path) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr("piperch.services.storage.shutil.copy2", fail_copy)
    try:
        selection = service.prepare_interactive()
        assert selection is not None

        await service.migrate(selection.target)

        assert supervisor.stopped
        assert restarted == [True]
        assert settings.get().library_root == source
        assert (source / "keep.txt").read_text(encoding="utf-8") == "keep"
        assert target.is_dir() and not any(target.iterdir())
        assert not paths.storage_migration.exists()
    finally:
        database.close()


@pytest.mark.parametrize("switched", [False, True])
def test_storage_migration_recovery_uses_persisted_setting_as_authority(
    tmp_path: Path,
    switched: bool,
) -> None:
    paths, database, settings, _, _, _, service = _storage(tmp_path)
    source = settings.get().library_root
    (source / "source.txt").write_text("source", encoding="utf-8")
    target = tmp_path / "recovery-target"
    target.mkdir()
    migration_id = "recovery-id"
    (target / ".piperch-migration").write_text(migration_id, encoding="utf-8")
    (target / "copied.txt").write_text("copied", encoding="utf-8")
    journal = StorageMigrationJournal(
        token=migration_id,
        source=source,
        target=target,
        staging=target.with_name(f".{target.name}.piperch-migration-{migration_id}"),
    )
    paths.storage_migration.write_text(journal.model_dump_json(), encoding="utf-8")
    if switched:
        settings.set_library_root_after_migration(target)
    try:
        service.recover()

        assert not paths.storage_migration.exists()
        if switched:
            assert not source.exists()
            assert (target / "copied.txt").is_file()
            assert not (target / ".piperch-migration").exists()
        else:
            assert (source / "source.txt").is_file()
            assert target.is_dir() and not any(target.iterdir())
    finally:
        database.close()
