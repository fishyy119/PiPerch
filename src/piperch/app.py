# pyright: reportUnusedFunction=false
# FastAPI 通过装饰器注册局部处理函数，Pyright 无法识别这些函数在运行期被使用。
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable
from contextlib import asynccontextmanager
from importlib.resources import files
from mimetypes import guess_type
from pathlib import PurePosixPath
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from starlette.exceptions import HTTPException

from piperch import __version__
from piperch.api import authors, discovery, downloads, favorites, gallery, groups, pixiv_images, settings
from piperch.api.models import ErrorBody, ErrorResponse, HealthResponse
from piperch.container import AppContainer
from piperch.database import Database, run_migrations
from piperch.errors import AppError, NotFoundError
from piperch.paths import AppPaths
from piperch.pixiv import PixivClient
from piperch.repositories import ArtworkGroupRepository, ArtworkRepository, DownloadRepository, FavoriteRepository
from piperch.runtime import AppControl
from piperch.services.downloads import (
    ArtworkDownloadCommitService,
    ArtworkDownloadService,
    DownloadEventBroker,
    DownloadSupervisor,
)
from piperch.services.favorite_sync import FavoriteSyncService
from piperch.services.library import LibraryService
from piperch.services.library_files import LibraryFileOperations
from piperch.services.storage import StorageMigrationService
from piperch.services.tag_search import TagSearchIndex
from piperch.services.thumbnails import ArtworkThumbnailCache
from piperch.settings import SettingsManager

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


def create_app(paths: AppPaths | None = None, control: AppControl | None = None) -> FastAPI:
    resolved_paths = paths or AppPaths.from_data_dir()
    app_control = control or AppControl.standalone()
    frontend_dist = files("piperch").joinpath("frontend")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        resolved_paths.ensure_directories()
        _cleanup_staging(resolved_paths)
        run_migrations(resolved_paths)
        database = Database(resolved_paths.database)
        tag_search_index = TagSearchIndex(database)
        tag_search_index.synchronize()
        settings_manager = SettingsManager(resolved_paths.settings, resolved_paths.default_library)
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
        events = DownloadEventBroker()
        thumbnail_cache = ArtworkThumbnailCache(resolved_paths)
        library_files = LibraryFileOperations()
        download_commit_service = ArtworkDownloadCommitService(
            database,
            artwork_repository,
            favorite_repository,
            group_repository,
            tag_search_index,
        )
        download_service = ArtworkDownloadService(
            resolved_paths,
            settings_manager,
            artwork_repository,
            pixiv,
            download_commit_service,
            thumbnail_cache,
            library_files,
        )
        supervisor = DownloadSupervisor(download_repository, download_service, events, settings_manager)
        mutation_lock = Lock()
        library_service = LibraryService(
            resolved_paths,
            settings_manager,
            artwork_repository,
            thumbnail_cache,
            mutation_lock,
            library_files,
        )
        storage_service = StorageMigrationService(
            resolved_paths,
            settings_manager,
            download_repository,
            supervisor,
            app_control,
            mutation_lock,
        )
        storage_service.recover()
        settings_manager.get().library_root.mkdir(parents=True, exist_ok=True)
        library_service.recover_pending_deletes()
        container = AppContainer(
            paths=resolved_paths,
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
            instance_id=app_control.instance_id,
        )
        app.state.container = container
        await supervisor.start()
        try:
            yield
        finally:
            await shutdown_resources(supervisor, pixiv, database)

    application = FastAPI(
        title="PiPerch API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(AppError)
    async def app_error_handler(_request: Request, error: AppError) -> JSONResponse:
        response = ErrorResponse(error=ErrorBody(code=error.code, message=error.message, details=error.details))
        return JSONResponse(
            status_code=error.status_code,
            content=response.model_dump(by_alias=True, exclude_none=True),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        response = ErrorResponse(
            error=ErrorBody(
                code="validation_error",
                message="请求参数不符合要求。",
                details={"errors": jsonable_encoder(error.errors())},
            )
        )
        return JSONResponse(status_code=422, content=response.model_dump(by_alias=True))

    @application.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, error: HTTPException) -> JSONResponse:
        messages = {
            404: "请求的资源不存在。",
            405: "该接口不支持当前请求方法。",
        }
        response = ErrorResponse(
            error=ErrorBody(
                code="not_found" if error.status_code == 404 else "http_error",
                message=messages.get(error.status_code, "HTTP 请求失败。"),
            )
        )
        return JSONResponse(
            status_code=error.status_code,
            content=response.model_dump(by_alias=True, exclude_none=True),
            headers=error.headers,
        )

    @application.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health(request: Request) -> HealthResponse:
        container: AppContainer = request.app.state.container
        with container.database.connect() as connection:
            connection.execute(text("SELECT 1"))
        return HealthResponse(instance_id=container.instance_id)

    application.include_router(settings.router, prefix="/api")
    application.include_router(authors.router, prefix="/api")
    application.include_router(discovery.router, prefix="/api")
    application.include_router(pixiv_images.router, prefix="/api")
    application.include_router(downloads.router, prefix="/api")
    application.include_router(downloads.events_router, prefix="/api")
    application.include_router(favorites.router, prefix="/api")
    application.include_router(groups.router, prefix="/api")
    application.include_router(gallery.router, prefix="/api")

    @application.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> Response:
        if full_path == "api" or full_path.startswith("api/"):
            raise NotFoundError("API 接口不存在。")
        relative_path = PurePosixPath(full_path)
        if full_path and "\\" not in full_path and not relative_path.is_absolute() and ".." not in relative_path.parts:
            requested = frontend_dist.joinpath(*relative_path.parts)
            if requested.is_file():
                return Response(
                    content=requested.read_bytes(),
                    media_type=guess_type(requested.name)[0] or "application/octet-stream",
                )
        index = frontend_dist.joinpath("index.html")
        if index.is_file():
            return Response(content=index.read_bytes(), media_type="text/html")
        raise NotFoundError("安装包不包含前端资源，请重新安装 PiPerch。")

    return application


app = create_app()
