# pyright: reportUnusedFunction=false
# FastAPI 通过装饰器注册局部处理函数，Pyright 无法识别这些函数在运行期被使用。
from __future__ import annotations

from functools import partial
from importlib.resources import files
from mimetypes import guess_type
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

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
from piperch.application.control import AppControl
from piperch.application.lifecycle import lifespan
from piperch.errors import AppError, NotFoundError
from piperch.paths import AppPaths

if TYPE_CHECKING:
    from piperch.application.container import AppContainer


def create_app(paths: AppPaths | None = None, control: AppControl | None = None) -> FastAPI:
    resolved_paths = paths or AppPaths.from_data_dir()
    app_control = control or AppControl.standalone()
    frontend_dist = files("piperch").joinpath("frontend")

    application = FastAPI(
        title="PiPerch API",
        version=__version__,
        lifespan=partial(lifespan, paths=resolved_paths, control=app_control),
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
