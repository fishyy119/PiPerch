from __future__ import annotations

import asyncio
import json
import mimetypes
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import TYPE_CHECKING, cast
from urllib.parse import urlparse

import anyio
import httpx
from anyio import to_thread

from piperch.errors import UpstreamError
from piperch.pixiv.parsing import as_mapping, as_text

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping, Sequence
    from pathlib import Path

_PIXIV_API_HOST = "www.pixiv.net"
_MAX_THUMBNAIL_BYTES = 16 * 1024 * 1024


class _PixivAuthPageParser(HTMLParser):
    """提取 Pixiv 登录页中两种常见的认证数据载体。"""

    def __init__(self) -> None:
        super().__init__()
        self.global_data: str | None = None
        self.next_data_parts: list[str] = []
        self._in_next_data = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "global-data":
            self.global_data = attributes.get("content")
        elif tag == "script" and attributes.get("id") == "__NEXT_DATA__":
            self._in_next_data = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_next_data:
            self._in_next_data = False

    def handle_data(self, data: str) -> None:
        if self._in_next_data:
            self.next_data_parts.append(data)


def _json_mapping(value: str) -> Mapping[str, object]:
    try:
        return as_mapping(cast("object", json.loads(value)))
    except (json.JSONDecodeError, TypeError):
        return {}


def _csrf_token_from_html(document: str) -> str | None:
    parser = _PixivAuthPageParser()
    parser.feed(document)

    if parser.global_data:
        token = as_text(_json_mapping(parser.global_data).get("token"))
        if token:
            return token

    next_data = _json_mapping("".join(parser.next_data_parts))
    page_props = as_mapping(as_mapping(next_data.get("props")).get("pageProps"))
    serialized_state = page_props.get("serverSerializedPreloadedState")
    state = _json_mapping(serialized_state) if isinstance(serialized_state, str) else as_mapping(serialized_state)
    token = as_text(as_mapping(state.get("api")).get("token"))
    return token or None


class PixivTransport:
    """集中处理 HTTPX 生命周期、限速、重试和下载主机校验。"""

    def __init__(self, *, proxy_url: str | None, request_interval_ms: int) -> None:
        self._client = self._build_client(proxy_url)
        self._proxy_url = proxy_url
        self._request_interval = request_interval_ms / 1000
        self._metadata_lock = asyncio.Lock()
        self._reconfigure_lock = asyncio.Lock()
        self._client_condition = asyncio.Condition()
        self._active_requests = 0
        self._reconfiguring = False
        self._last_metadata_request = 0.0
        self._csrf_cookie: str | None = None
        self._cached_csrf_token: str | None = None

    @staticmethod
    def _build_client(proxy_url: str | None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            proxy=proxy_url,
            follow_redirects=True,
            timeout=httpx.Timeout(connect=10, read=60, write=60, pool=10),
            limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
            headers={
                "Accept": "application/json, text/plain, */*",
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"),
                "Referer": "https://www.pixiv.net/",
            },
        )

    async def reconfigure(self, proxy_url: str | None, request_interval_ms: int) -> None:
        async with self._reconfigure_lock:
            self._request_interval = request_interval_ms / 1000
            if proxy_url == self._proxy_url:
                return
            replacement = self._build_client(proxy_url)
            async with self._client_condition:
                self._reconfiguring = True
                try:
                    await self._client_condition.wait_for(lambda: self._active_requests == 0)
                    previous = self._client
                    self._client = replacement
                    self._proxy_url = proxy_url
                finally:
                    self._reconfiguring = False
                    self._client_condition.notify_all()
            await previous.aclose()

    async def close(self) -> None:
        async with self._reconfigure_lock:
            async with self._client_condition:
                self._reconfiguring = True
                await self._client_condition.wait_for(lambda: self._active_requests == 0)
                client = self._client
            await client.aclose()

    @asynccontextmanager
    async def _use_client(self) -> AsyncGenerator[httpx.AsyncClient]:
        async with self._client_condition:
            await self._client_condition.wait_for(lambda: not self._reconfiguring)
            self._active_requests += 1
            client = self._client
        try:
            yield client
        finally:
            async with self._client_condition:
                self._active_requests -= 1
                self._client_condition.notify_all()

    async def get_body(
        self,
        path: str,
        *,
        cookie: str | None,
        params: httpx.QueryParams | Mapping[str, str | int] | None = None,
    ) -> Mapping[str, object] | Sequence[object]:
        async with self._metadata_lock:
            remaining = self._request_interval - (time.monotonic() - self._last_metadata_request)
            if remaining > 0:
                await asyncio.sleep(remaining)
            response = await self._request(
                "GET",
                f"https://{_PIXIV_API_HOST}{path}",
                cookie=cookie,
                params=params,
            )
            self._last_metadata_request = time.monotonic()
        payload = cast("object", response.json())
        root = as_mapping(payload)
        if root.get("error") is True:
            message = as_text(root.get("message")) or "Pixiv 返回了错误。"
            raise UpstreamError("pixiv_error", message, 401 if response.status_code in {401, 403} else 502)
        body = root.get("body")
        if not isinstance(body, (dict, list)):
            raise UpstreamError("invalid_pixiv_response", "Pixiv 返回的数据结构无效。")
        return cast("Mapping[str, object] | Sequence[object]", body)

    async def post_form(
        self,
        path: str,
        *,
        cookie: str | None,
        data: Mapping[str, str | int],
    ) -> None:
        """携带当前会话的 CSRF token 提交 Pixiv 表单写请求。"""
        if not cookie:
            raise UpstreamError(
                "pixiv_cookie_required",
                "请先在设置中保存包含 PHPSESSID 的 Pixiv Cookie。",
                401,
            )

        for attempt in range(2):
            token = await self._get_csrf_token(cookie, force_refresh=attempt > 0)
            try:
                async with self._metadata_lock:
                    remaining = self._request_interval - (time.monotonic() - self._last_metadata_request)
                    if remaining > 0:
                        await asyncio.sleep(remaining)
                    response = await self._request(
                        "POST",
                        f"https://{_PIXIV_API_HOST}{path}",
                        cookie=cookie,
                        data=data,
                        headers={
                            "Origin": f"https://{_PIXIV_API_HOST}",
                            "X-CSRF-TOKEN": token,
                        },
                    )
                    self._last_metadata_request = time.monotonic()
            except UpstreamError as error:
                if error.status_code == 403 and attempt == 0:
                    self._invalidate_csrf_token(cookie)
                    continue
                raise

            try:
                payload = cast("object", response.json())
            except ValueError as error:
                raise UpstreamError("invalid_pixiv_response", "Pixiv 返回的数据结构无效。") from error
            root = as_mapping(payload)
            if root.get("error") is True:
                message = as_text(root.get("message")) or "Pixiv 返回了错误。"
                raise UpstreamError("pixiv_error", message)
            return

        raise UpstreamError("pixiv_http_error", "Pixiv 拒绝了当前请求，请检查 Cookie 和访问频率。", 403)

    async def _get_csrf_token(self, cookie: str, *, force_refresh: bool = False) -> str:
        if not force_refresh and cookie == self._csrf_cookie and self._cached_csrf_token:
            return self._cached_csrf_token

        async with self._metadata_lock:
            if not force_refresh and cookie == self._csrf_cookie and self._cached_csrf_token:
                return self._cached_csrf_token
            remaining = self._request_interval - (time.monotonic() - self._last_metadata_request)
            if remaining > 0:
                await asyncio.sleep(remaining)
            response = await self._request(
                "GET",
                f"https://{_PIXIV_API_HOST}/",
                cookie=cookie,
            )
            self._last_metadata_request = time.monotonic()

        token = _csrf_token_from_html(response.text)
        if token is None:
            raise UpstreamError(
                "pixiv_csrf_unavailable",
                "无法从 Pixiv 页面读取关注操作所需的安全令牌。",
            )
        self._csrf_cookie = cookie
        self._cached_csrf_token = token
        return token

    def _invalidate_csrf_token(self, cookie: str) -> None:
        if cookie == self._csrf_cookie:
            self._csrf_cookie = None
            self._cached_csrf_token = None

    async def fetch_thumbnail(self, url: str, cookie: str | None) -> tuple[bytes, str]:
        """读取受信任的 pximg 缩略图，并限制响应类型和大小。"""
        self._validate_media_url(url)
        for attempt in range(3):
            try:
                async with (
                    self._use_client() as client,
                    client.stream("GET", url, headers=self._cookie_headers(cookie)) as response,
                ):
                    await self._raise_for_status(response)
                    self._validate_media_url(str(response.url))
                    media_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if not media_type.startswith("image/"):
                        raise UpstreamError(
                            "invalid_thumbnail",
                            "Pixiv 缩略图返回了非图片内容。",
                        )
                    declared_size = response.headers.get("content-length", "")
                    if declared_size.isdigit() and int(declared_size) > _MAX_THUMBNAIL_BYTES:
                        raise UpstreamError("thumbnail_too_large", "Pixiv 缩略图文件过大。")

                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > _MAX_THUMBNAIL_BYTES:
                            raise UpstreamError("thumbnail_too_large", "Pixiv 缩略图文件过大。")
                        chunks.append(chunk)
                    return b"".join(chunks), media_type
            except httpx.HTTPStatusError as error:
                if not self._is_retryable_status(error.response.status_code):
                    raise UpstreamError(
                        "pixiv_http_error",
                        f"Pixiv 返回了 HTTP {error.response.status_code}。",
                    ) from error
                if attempt == 2:
                    raise UpstreamError("thumbnail_failed", "缩略图加载失败。") from error
                await self._retry_delay(attempt, error.response)
            except httpx.HTTPError as error:
                if attempt == 2:
                    raise UpstreamError("thumbnail_failed", "缩略图加载失败。") from error
                await self._retry_delay(attempt)
        raise UpstreamError("thumbnail_failed", "缩略图加载失败。")

    async def download(self, url: str, target: Path, cookie: str | None) -> tuple[str, int]:
        self._validate_media_url(url)
        part = target.with_name(f"{target.name}.part")
        part.parent.mkdir(parents=True, exist_ok=True)
        part.unlink(missing_ok=True)
        headers = self._cookie_headers(cookie)
        for attempt in range(3):
            try:
                async with (
                    self._use_client() as client,
                    client.stream("GET", url, headers=headers) as response,
                ):
                    await self._raise_for_status(response)
                    self._validate_media_url(str(response.url))
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    async with await anyio.open_file(part, "wb") as file_handle:
                        async for chunk in response.aiter_bytes():
                            await file_handle.write(chunk)
                size = part.stat().st_size
                if size <= 0:
                    raise UpstreamError("empty_download", "Pixiv 返回了空文件。")
                expected = response.headers.get("content-length")
                if expected and expected.isdigit() and int(expected) != size:
                    raise UpstreamError("truncated_download", "下载文件长度与响应声明不一致。")
                await to_thread.run_sync(part.replace, target)
                guessed = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                return content_type or guessed, size
            except UpstreamError as error:
                part.unlink(missing_ok=True)
                if error.code not in {"empty_download", "truncated_download"} or attempt == 2:
                    raise
                await self._retry_delay(attempt)
            except httpx.HTTPStatusError as error:
                part.unlink(missing_ok=True)
                if not self._is_retryable_status(error.response.status_code):
                    raise UpstreamError(
                        "pixiv_http_error",
                        f"Pixiv 返回了 HTTP {error.response.status_code}。",
                    ) from error
                if attempt == 2:
                    raise UpstreamError("download_failed", "媒体下载重试后仍然失败。") from error
                await self._retry_delay(attempt, error.response)
            except httpx.HTTPError as error:
                part.unlink(missing_ok=True)
                if attempt == 2:
                    raise UpstreamError("download_failed", "媒体下载重试后仍然失败。") from error
                await self._retry_delay(attempt)
        raise UpstreamError("download_failed", "下载失败。")

    async def _request(
        self,
        method: str,
        url: str,
        *,
        cookie: str | None,
        params: httpx.QueryParams | Mapping[str, str | int] | None = None,
        data: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        for attempt in range(3):
            try:
                request_headers = self._cookie_headers(cookie)
                if headers is not None:
                    request_headers.update(headers)
                async with self._use_client() as client:
                    response = await client.request(
                        method,
                        url,
                        params=params,
                        data=data,
                        headers=request_headers,
                    )
                self._validate_api_url(str(response.url))
                await self._raise_for_status(response)
                return response
            except httpx.HTTPStatusError as error:
                if not self._is_retryable_status(error.response.status_code):
                    raise UpstreamError(
                        "pixiv_http_error",
                        f"Pixiv 返回了 HTTP {error.response.status_code}。",
                    ) from error
                if attempt == 2:
                    raise UpstreamError("pixiv_unreachable", "Pixiv 服务暂时不可用。") from error
                await self._retry_delay(attempt, error.response)
            except httpx.HTTPError as error:
                if attempt == 2:
                    raise UpstreamError("pixiv_unreachable", "无法连接 Pixiv。") from error
                await self._retry_delay(attempt)
        raise UpstreamError("pixiv_unreachable", "无法连接 Pixiv。")

    @staticmethod
    async def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code in {401, 403, 404}:
            messages = {
                401: "Pixiv Cookie 已失效或缺少权限。",
                403: "Pixiv 拒绝了当前请求，请检查 Cookie 和访问频率。",
                404: "Pixiv 中不存在对应内容。",
            }
            raise UpstreamError("pixiv_http_error", messages[response.status_code], response.status_code)
        response.raise_for_status()

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code in {408, 429} or status_code >= 500

    @staticmethod
    async def _retry_delay(attempt: int, response: httpx.Response | None = None) -> None:
        delay = float(2**attempt)
        retry_after = response.headers.get("retry-after") if response is not None else None
        if retry_after:
            if retry_after.isdigit():
                delay = max(delay, float(retry_after))
            else:
                try:
                    parsed = parsedate_to_datetime(retry_after)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    delay = max(delay, (parsed - datetime.now(UTC)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
        await asyncio.sleep(min(60, max(0, delay)))

    @staticmethod
    def _cookie_headers(cookie: str | None) -> dict[str, str]:
        return {"Cookie": cookie} if cookie else {}

    @staticmethod
    def _validate_api_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != _PIXIV_API_HOST:
            raise UpstreamError("unsafe_redirect", "Pixiv 请求被重定向到不受信任的主机。")

    @staticmethod
    def _validate_media_url(url: str) -> None:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or not (host == "pximg.net" or host.endswith(".pximg.net")):
            raise UpstreamError("unsafe_media_url", "媒体地址不是受信任的 pximg HTTPS 地址。")
