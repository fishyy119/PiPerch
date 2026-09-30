from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from httpx import Response


class ApiTestClient(Protocol):
    """测试只依赖同步客户端中实际使用的最小接口。"""

    def get(self, url: str) -> Response: ...

    def post(self, url: str, *, json: object) -> Response: ...

    def put(self, url: str, *, json: object) -> Response: ...

    def delete(self, url: str) -> Response: ...
