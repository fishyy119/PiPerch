from __future__ import annotations

from pathlib import Path

from anyio import to_thread
from fastapi import APIRouter, Depends

from piperch.api.dependencies import get_container
from piperch.api.models import (
    CookieValidationRequest,
    CookieValidationResponse,
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
    if "library_root" in changes:
        changes["library_root"] = Path(changes["library_root"])
    settings = await to_thread.run_sync(lambda: container.settings.patch(**changes))
    if {"proxy_url", "request_interval_ms"} & changes.keys():
        await container.pixiv.reconfigure(settings.proxy_url, settings.request_interval_ms)
    return _response(settings)


@router.post("/pixiv-cookie/validate", response_model=CookieValidationResponse)
async def validate_cookie(
    request: CookieValidationRequest,
    container: AppContainer = Depends(get_container),
) -> CookieValidationResponse:
    valid = await container.pixiv.validate_cookie(request.value)
    return CookieValidationResponse(valid=valid)
