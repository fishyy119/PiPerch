"""FANBOX 归档的 HTTP、重试、受信任地址校验与图片下载。"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast
from urllib.parse import urljoin, urlsplit

import anyio
import httpx
from anyio import to_thread
from PIL import Image

from piperch.errors import UpstreamError
from piperch.utils.http_client import HttpClientLifecycle

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

BASE_URL = "https://pawchive.pw"


class FanboxTransport:
    def __init__(self, *, proxy_url: str | None, request_interval_ms: int) -> None:
        self._http = HttpClientLifecycle(self._build_client, proxy_url)
        self._request_interval = request_interval_ms / 1000
        self._metadata_lock = asyncio.Lock()
        self._last_request = 0.0

    @staticmethod
    def _build_client(proxy_url: str | None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            proxy=proxy_url,
            follow_redirects=False,
            timeout=httpx.Timeout(connect=10, read=60, write=60, pool=10),
            limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
            headers={"User-Agent": "PiPerch", "Referer": f"{BASE_URL}/"},
        )

    async def reconfigure(self, proxy_url: str | None, request_interval_ms: int) -> None:
        self._request_interval = request_interval_ms / 1000
        await self._http.reconfigure(proxy_url)

    async def close(self) -> None:
        await self._http.close()

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or not (
                host in {"pawchive.pw", "file.pawchive.pw", "img.pawchive.pw"}
                or re.fullmatch(r"n[1-9]\d*\.pawchive\.pw", host)
            )
        ):
            raise UpstreamError("unsafe_fanbox_url", "FANBOX 资源地址不是受信任的归档 HTTPS 地址。")

    @asynccontextmanager
    async def _response(self, url: str) -> AsyncGenerator[httpx.Response]:
        async with self._http.use() as client:
            for _redirect in range(6):
                self._validate_url(url)
                async with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    response.raise_for_status()
                    yield response
                    return
            raise UpstreamError("fanbox_redirect_limit", "FANBOX 资源重定向次数过多。")

    async def _request_metadata(self, url: str, *, json_response: bool = True) -> object:
        async with self._metadata_lock:
            remaining = self._request_interval - (time.monotonic() - self._last_request)
            if remaining > 0:
                await asyncio.sleep(remaining)
            try:
                for attempt in range(3):
                    try:
                        async with self._response(url) as response:
                            await response.aread()
                            return cast("object", response.json()) if json_response else response.text
                    except httpx.HTTPStatusError as error:
                        if error.response.status_code == 404:
                            raise UpstreamError(
                                "fanbox_not_found", "归档中未找到该 FANBOX 作者或投稿。", 404
                            ) from error
                        if error.response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                            raise UpstreamError(
                                "fanbox_http_error", f"FANBOX 归档返回了 HTTP {error.response.status_code}。"
                            ) from error
                    except httpx.HTTPError as error:
                        if attempt == 2:
                            raise UpstreamError("fanbox_request_failed", "FANBOX 归档请求失败。") from error
                    except (json.JSONDecodeError, UnicodeDecodeError) as error:
                        raise UpstreamError("invalid_fanbox_response", "FANBOX 归档返回的数据无效。") from error
                    await asyncio.sleep(2**attempt)
            finally:
                self._last_request = time.monotonic()
        raise UpstreamError("fanbox_request_failed", "FANBOX 归档请求失败。")

    async def get_json(self, path: str) -> object:
        return await self._request_metadata(f"{BASE_URL}/api/v1{path}")

    async def get_text(self, path: str) -> str:
        return cast("str", await self._request_metadata(f"{BASE_URL}{path}", json_response=False))

    async def fetch_thumbnail(self, url: str) -> tuple[bytes, str]:
        try:
            async with self._response(url) as response:
                mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if not mime.startswith("image/"):
                    raise UpstreamError("invalid_thumbnail", "FANBOX 预览返回了非图片内容。")
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > 16 * 1024 * 1024:
                        raise UpstreamError("thumbnail_too_large", "FANBOX 预览图片过大。")
                    chunks.append(chunk)
                return b"".join(chunks), mime
        except httpx.HTTPError as error:
            raise UpstreamError("fanbox_preview_failed", "FANBOX 预览加载失败。") from error

    async def download(self, url: str, target: Path) -> tuple[str, int]:
        part = target.with_name(f"{target.name}.part")
        try:
            for attempt in range(3):
                try:
                    async with self._response(url) as response:
                        mime = response.headers.get("content-type", "").split(";", 1)[0]
                        if mime == "application/octet-stream" or not mime:
                            mime = mimetypes.guess_type(urlsplit(url).path)[0] or ""
                        if not mime.startswith("image/"):
                            raise UpstreamError("invalid_media_type", "FANBOX 附件返回了非图片内容。")
                        async with await anyio.open_file(part, "wb") as output:
                            async for chunk in response.aiter_bytes():
                                await output.write(chunk)
                        size = part.stat().st_size
                        expected = response.headers.get("content-length", "")
                        if size <= 0 or (
                            expected.isdigit()
                            and not response.headers.get("content-encoding")
                            and int(expected) != size
                        ):
                            raise UpstreamError("truncated_download", "FANBOX 图片下载不完整。")
                    await to_thread.run_sync(self._validate_image, part)
                    part.replace(target)
                    return mime, size
                except (httpx.HTTPError, UpstreamError) as error:
                    if isinstance(error, UpstreamError) and error.code != "truncated_download":
                        raise
                    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 404:
                        raise UpstreamError(
                            "fanbox_image_not_found", "归档中的 FANBOX 图片资源不存在。", 404
                        ) from error
                    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code not in {
                        429,
                        500,
                        502,
                        503,
                        504,
                    }:
                        raise UpstreamError("fanbox_download_failed", "FANBOX 图片下载失败。") from error
                    if attempt == 2:
                        raise UpstreamError("fanbox_download_failed", "FANBOX 图片下载重试后仍然失败。") from error
                    await asyncio.sleep(2**attempt)
        finally:
            part.unlink(missing_ok=True)
        raise UpstreamError("fanbox_download_failed", "FANBOX 图片下载失败。")

    @staticmethod
    def _validate_image(path: Path) -> None:
        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, ValueError) as error:
            raise UpstreamError("invalid_fanbox_image", "FANBOX 附件不是有效的图片文件。") from error
