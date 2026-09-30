from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("not_found", message, 404)


class ConflictError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, 409)


class UpstreamError(AppError):
    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(code, message, status_code)
