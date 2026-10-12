from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from piperch.services.events import AppEventBroker


class LibraryCommitCoordinator:
    """串行提交图库增删，并在释放锁前发布对应事件。"""

    def __init__(self, events: AppEventBroker) -> None:
        self._lock = Lock()
        self._events = events

    def commit_addition(self, artwork_id: int, commit: Callable[[], None]) -> None:
        # 添加和删除共用提交锁，事件入队后才允许下一个状态变更提交。
        with self._lock:
            commit()
            self._events.publish_library_change((artwork_id,), in_library=True)

    def commit_removal(self, commit: Callable[[], set[int]]) -> set[int]:
        with self._lock:
            deleted_ids = commit()
            self._events.publish_library_change(sorted(deleted_ids), in_library=False)
            return deleted_ids
