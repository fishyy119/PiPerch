from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class AppControl:
    """承载单次应用实例标识与由宿主提供的重启请求。"""

    instance_id: str
    request_restart: Callable[[], None]

    @classmethod
    def standalone(cls) -> AppControl:
        return cls(instance_id=str(uuid4()), request_restart=lambda: None)
