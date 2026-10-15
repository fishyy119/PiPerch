from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from threading import Lock
from typing import TYPE_CHECKING

from piperch.application.container import AppContainer
from piperch.database import Database, run_migrations
from piperch.pixiv import PixivClient
from piperch.repositories import ArtworkGroupRepository, ArtworkRepository, DownloadRepository, FavoriteRepository
from piperch.services.downloads import ArtworkDownloadCommitService, ArtworkDownloadService, DownloadSupervisor
from piperch.services.events import AppEventBroker
from piperch.services.favorite_sync import FavoriteSyncService
from piperch.services.library import LibraryService
from piperch.services.library_commits import LibraryCommitCoordinator
from piperch.services.library_files import LibraryFileOperations
from piperch.services.storage import StorageMigrationService
from piperch.services.tag_search import TagSearchIndex
from piperch.services.thumbnails import ArtworkThumbnailCache
from piperch.settings import SettingsManager

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable

    from fastapi import FastAPI

    from piperch.application.control import AppControl
    from piperch.paths import AppPaths

logger = logging.getLogger(__name__)

_SUPERVISOR_STOP_TIMEOUT_SECONDS = 3
_HTTP_CLOSE_TIMEOUT_SECONDS = 2


def _cleanup_staging(paths: AppPaths) -> None:
    for part in paths.staging.rglob("*.part"):
        part.unlink(missing_ok=True)


async def _run_shutdown_step(name: str, operation: Awaitable[None], timeout_seconds: float) -> None:
    try:
        async with asyncio.timeout(timeout_seconds):
            await operation
    except TimeoutError:
        logger.error("%s 未能在 %.1f 秒内结束，继续释放其余资源。", name, timeout_seconds)
    except Exception:
        logger.exception("%s 关闭失败，继续释放其余资源。", name)


async def shutdown_resources(
    supervisor: DownloadSupervisor,
    pixiv: PixivClient,
    database: Database,
    *,
    supervisor_timeout_seconds: float = _SUPERVISOR_STOP_TIMEOUT_SECONDS,
    http_timeout_seconds: float = _HTTP_CLOSE_TIMEOUT_SECONDS,
) -> None:
    """按依赖顺序关闭资源，并避免单个组件让整个进程永久滞留。"""
    try:
        await _run_shutdown_step("下载监督器", supervisor.stop(), supervisor_timeout_seconds)
        await _run_shutdown_step("Pixiv HTTP 客户端", pixiv.close(), http_timeout_seconds)
    finally:
        database.close()


@asynccontextmanager
async def lifespan(app: FastAPI, *, paths: AppPaths, control: AppControl) -> AsyncGenerator[None]:
    paths.ensure_directories()
    _cleanup_staging(paths)
    run_migrations(paths)
    database = Database(paths.database)
    tag_search_index = TagSearchIndex(database)
    tag_search_index.synchronize()
    settings_manager = SettingsManager(paths.settings, paths.default_library)
    settings_manager.initialize()
    current_settings = settings_manager.get()
    pixiv = PixivClient(
        proxy_url=current_settings.proxy_url,
        request_interval_ms=current_settings.request_interval_ms,
    )
    artwork_repository = ArtworkRepository(database)
    favorite_repository = FavoriteRepository(database)
    favorite_sync_service = FavoriteSyncService(favorite_repository)
    group_repository = ArtworkGroupRepository(database)
    download_repository = DownloadRepository(database)
    events = AppEventBroker()
    thumbnail_cache = ArtworkThumbnailCache(paths)
    library_files = LibraryFileOperations()
    library_commits = LibraryCommitCoordinator(events)
    download_commit_service = ArtworkDownloadCommitService(
        database,
        artwork_repository,
        favorite_repository,
        group_repository,
        tag_search_index,
        library_commits=library_commits,
    )
    download_service = ArtworkDownloadService(
        paths,
        settings_manager,
        artwork_repository,
        pixiv,
        download_commit_service,
        favorite_repository,
        thumbnail_cache,
        library_files,
    )
    supervisor = DownloadSupervisor(download_repository, download_service, events, settings_manager)
    mutation_lock = Lock()
    library_service = LibraryService(
        paths,
        settings_manager,
        artwork_repository,
        thumbnail_cache,
        mutation_lock,
        library_files,
        library_commits=library_commits,
    )
    storage_service = StorageMigrationService(
        paths,
        settings_manager,
        download_repository,
        supervisor,
        control,
        mutation_lock,
    )
    storage_service.recover()
    settings_manager.get().library_root.mkdir(parents=True, exist_ok=True)
    library_service.recover_pending_deletes()
    container = AppContainer(
        paths=paths,
        database=database,
        settings=settings_manager,
        artworks=artwork_repository,
        favorites=favorite_repository,
        favorite_sync=favorite_sync_service,
        groups=group_repository,
        downloads=download_repository,
        download_commits=download_commit_service,
        pixiv=pixiv,
        supervisor=supervisor,
        events=events,
        library=library_service,
        thumbnails=thumbnail_cache,
        storage=storage_service,
        instance_id=control.instance_id,
    )
    app.state.container = container
    await supervisor.start()
    try:
        yield
    finally:
        await shutdown_resources(supervisor, pixiv, database)
