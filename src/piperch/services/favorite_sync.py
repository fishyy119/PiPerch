from __future__ import annotations

from dataclasses import dataclass, replace
from threading import Lock
from time import monotonic
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from anyio import to_thread

from piperch.errors import ConflictError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from piperch.domain.favorites import FavoriteSyncDiff, FavoriteSyncResult
    from piperch.pixiv import PixivClient
    from piperch.repositories import FavoriteRepository


@dataclass(frozen=True, slots=True)
class FavoriteSyncPlan:
    plan_id: UUID
    diff: FavoriteSyncDiff


class FavoriteSyncService:
    def __init__(
        self,
        favorites: FavoriteRepository,
        pixiv: PixivClient,
        *,
        plan_ttl_seconds: int = 600,
    ) -> None:
        self._favorites = favorites
        self._pixiv = pixiv
        self._plan_ttl_seconds = plan_ttl_seconds
        self._lock = Lock()
        self._active_plan: FavoriteSyncPlan | None = None
        self._expires_at = 0.0

    async def create_plan(self, remote_artwork_ids: Sequence[int], cookie: str | None) -> FavoriteSyncPlan:
        diff = await to_thread.run_sync(lambda: self._favorites.compare_with_remote(remote_artwork_ids))
        remote_ids = await to_thread.run_sync(self._favorites.remote_ids_for_local, diff.remove_artwork_ids)
        # 仅复核拟取消的本地收藏，保留 Pixiv 详情已返回 404 的作品。
        removals = [
            artwork_id
            for artwork_id in diff.remove_artwork_ids
            if artwork_id in remote_ids and await self._pixiv.artwork_exists(remote_ids[artwork_id], cookie)
        ]
        plan = FavoriteSyncPlan(
            plan_id=uuid4(),
            diff=replace(
                diff,
                remove_artwork_ids=tuple(removals),
                preserved_favorite_count=len(diff.remove_artwork_ids) - len(removals),
            ),
        )
        with self._lock:
            self._active_plan = plan
            self._expires_at = monotonic() + self._plan_ttl_seconds
        return plan

    def apply_plan(self, plan_id: UUID) -> FavoriteSyncResult:
        with self._lock:
            plan = self._active_plan
            if plan is None or plan.plan_id != plan_id or monotonic() >= self._expires_at:
                self._active_plan = None
                self._expires_at = 0.0
                raise ConflictError(
                    "favorite_sync_plan_expired",
                    "收藏同步摘要已失效，请重新检查 Pixiv 收藏。",
                )
            self._active_plan = None
            self._expires_at = 0.0
            return self._favorites.apply_sync(
                add_artwork_ids=plan.diff.add_artwork_ids,
                remove_artwork_ids=plan.diff.remove_artwork_ids,
            )
