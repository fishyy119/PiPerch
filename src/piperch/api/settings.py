from __future__ import annotations

from pathlib import Path

from anyio import to_thread
from fastapi import APIRouter, Depends

from piperch.api.dependencies import get_container
from piperch.api.models import (
    CookieValidationRequest,
    CookieValidationResponse,
    SettingsResponse,
    SettingsUpdate,
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


@router.put("", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdate,
    container: AppContainer = Depends(get_container),
) -> SettingsResponse:
    settings = await to_thread.run_sync(
        lambda: container.settings.update(
            pixiv_cookie=request.pixiv_cookie,
            proxy_url=request.proxy_url,
            library_root=Path(request.library_root),
            download_concurrency=request.download_concurrency,
            request_interval_ms=request.request_interval_ms,
            webp_enabled=request.webp_enabled,
            webp_quality=request.webp_quality,
        )
    )
    await container.pixiv.reconfigure(settings.proxy_url, settings.request_interval_ms)
    return _response(settings)


@router.post("/pixiv-cookie/validate", response_model=CookieValidationResponse)
async def validate_cookie(
    request: CookieValidationRequest,
    container: AppContainer = Depends(get_container),
) -> CookieValidationResponse:
    valid = await container.pixiv.validate_cookie(request.value)
    return CookieValidationResponse(valid=valid)
