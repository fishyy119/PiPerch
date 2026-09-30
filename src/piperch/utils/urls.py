from urllib.parse import urlsplit, urlunsplit

import httpx


def normalize_proxy_url(url: str | None) -> str | None:
    if url is None or not url.strip():
        return None
    normalized = url.strip()
    try:
        parsed = urlsplit(normalized)
        _ = parsed.port
    except ValueError as error:
        raise ValueError("代理地址格式无效。") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("代理地址必须使用 http:// 或 https://。")
    try:
        httpx.Proxy(normalized)
    except (httpx.InvalidURL, ValueError) as error:
        raise ValueError("代理地址格式无效。") from error
    return normalized


def redact_url_password(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.password is None:
        return url
    user = parsed.username or ""
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{user}:***@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
