from __future__ import annotations

from anyio import to_thread
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask

from piperch.api.dependencies import get_container
from piperch.api.models import (
    CookieValidationRequest,
    CookieValidationResponse,
    LibraryMigrationCancelledResponse,
    LibraryMigrationResponse,
    LibraryMigrationStartedResponse,
    SettingsPatch,
    SettingsResponse,
)
from piperch.container import AppContainer
from piperch.domain import AppSettings
from piperch.utils.urls import redact_url_password

router = APIRouter(prefix="/settings", tags=["settings"])


def _response(settings: AppSettings) -> SettingsResponse:
    return SettingsResponse(
        pixiv_cookie=settings.pixiv_cookie,
        proxy_url=redact_url_password(settings.proxy_url),
        library_root=str(settings.library_root),
        download_concurrency=settings.download_concurrency,
        request_interval_ms=settings.request_interval_ms,
        webp_enabled=settings.webp_enabled,
        webp_quality=settings.webp_quality,
    )


@router.get("", response_model=SettingsResponse)
def get_settings(container: AppContainer = Depends(get_container)) -> SettingsResponse:
    return _response(container.settings.get())


@router.patch("", response_model=SettingsResponse)
async def patch_settings(
    request: SettingsPatch,
    container: AppContainer = Depends(get_container),
) -> SettingsResponse:
    changes = request.model_dump(exclude_unset=True)
    settings = await to_thread.run_sync(lambda: container.settings.patch(**changes))
    if {"proxy_url", "request_interval_ms"} & changes.keys():
        await container.pixiv.reconfigure(settings.proxy_url, settings.request_interval_ms)
    return _response(settings)


@router.post("/library-root/migrate", response_model=LibraryMigrationResponse)
async def migrate_library_root(
    container: AppContainer = Depends(get_container),
) -> LibraryMigrationCancelledResponse | JSONResponse:
    selection = await to_thread.run_sync(container.storage.prepare_interactive)
    if selection is None:
        return LibraryMigrationCancelledResponse(message="已取消图库迁移。")
    response = LibraryMigrationStartedResponse(
        message="图库迁移已开始，后续状态请查看后端终端。",
        target_path=str(selection.target),
        instance_id=container.instance_id,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(mode="json", by_alias=True),
        background=BackgroundTask(container.storage.migrate, selection.target),
    )


@router.post("/pixiv-cookie/validate", response_model=CookieValidationResponse)
async def validate_cookie(
    request: CookieValidationRequest,
    container: AppContainer = Depends(get_container),
) -> CookieValidationResponse:
    valid = await container.pixiv.validate_cookie(request.value)
    return CookieValidationResponse(valid=valid)
