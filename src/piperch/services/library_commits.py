from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

from piperch.domain.sources import LibraryArtworkReference

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from piperch.domain.sources import ArtworkSource
    from piperch.services.events import AppEventBroker


class LibraryCommitCoordinator:
    """串行提交图库增删，并在释放锁前发布对应事件。"""

    def __init__(self, events: AppEventBroker) -> None:
        self._lock = Lock()
        self._events = events

    def commit_addition(self, commit: Callable[[], int], *, source: ArtworkSource, remote_id: int) -> int:
        # 添加和删除共用提交锁，事件入队后才允许下一个状态变更提交。
        with self._lock:
            artwork_id = commit()
            self._events.publish_library_change(
                (LibraryArtworkReference(artwork_id, source, remote_id),), in_library=True
            )
            return artwork_id

    def commit_removal(
        self, commit: Callable[[], set[int]], *, references: Sequence[LibraryArtworkReference]
    ) -> set[int]:
        with self._lock:
            deleted_ids = commit()
            self._events.publish_library_change(
                tuple(reference for reference in references if reference.local_artwork_id in deleted_ids),
                in_library=False,
            )
            return deleted_ids
