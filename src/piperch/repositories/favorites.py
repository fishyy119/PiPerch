from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import bindparam, delete, insert, select, update

from piperch.database.tables import artworks, favorite_artworks
from piperch.domain import FavoriteState, FavoriteSyncDiff, FavoriteSyncResult
from piperch.errors import NotFoundError
from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine import Connection

    from piperch.database import Database


class FavoriteRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_state(self, artwork_id: int) -> FavoriteState:
        with self._database.connect() as connection:
            self._require_artwork(connection, artwork_id)
            return self._state(connection, artwork_id)

    def replace_state(self, artwork_id: int, *, is_favorite: bool) -> FavoriteState:
        now = utc_now_text()
        with self._database.begin() as connection:
            self._require_artwork(connection, artwork_id)
            if is_favorite:
                self._ensure_favorite(connection, artwork_id, now)
            else:
                connection.execute(delete(favorite_artworks).where(favorite_artworks.c.artwork_id == artwork_id))
            return self._state(connection, artwork_id)

    def compare_with_remote(self, remote_artwork_ids: Sequence[int]) -> FavoriteSyncDiff:
        remote_ids = set(remote_artwork_ids)
        with self._database.connect() as connection:
            local_ids = set(connection.scalars(select(artworks.c.id)))
            local_favorite_ids = set(connection.scalars(select(favorite_artworks.c.artwork_id)))
        matched_favorite_ids = remote_ids & local_ids
        return FavoriteSyncDiff(
            pixiv_favorite_count=len(remote_ids),
            local_artwork_count=len(local_ids),
            local_favorite_count=len(local_favorite_ids),
            matched_favorite_count=len(matched_favorite_ids),
            unavailable_locally_count=len(remote_ids - local_ids),
            add_artwork_ids=tuple(sorted(matched_favorite_ids - local_favorite_ids)),
            remove_artwork_ids=tuple(sorted(local_favorite_ids - remote_ids)),
        )

    def apply_sync(
        self,
        *,
        add_artwork_ids: Sequence[int],
        remove_artwork_ids: Sequence[int],
    ) -> FavoriteSyncResult:
        requested_additions = set(add_artwork_ids)
        requested_removals = set(remove_artwork_ids)
        now = utc_now_text()
        with self._database.begin() as connection:
            local_ids = set(connection.scalars(select(artworks.c.id)))
            local_favorite_ids = set(connection.scalars(select(favorite_artworks.c.artwork_id)))
            additions = sorted((requested_additions & local_ids) - local_favorite_ids)
            removals = sorted(requested_removals & local_favorite_ids)
            if additions:
                connection.execute(
                    insert(favorite_artworks),
                    [{"artwork_id": artwork_id, "created_at": now, "updated_at": now} for artwork_id in additions],
                )
            if removals:
                connection.execute(
                    delete(favorite_artworks).where(favorite_artworks.c.artwork_id == bindparam("target_artwork_id")),
                    [{"target_artwork_id": artwork_id} for artwork_id in removals],
                )
        return FavoriteSyncResult(added=len(additions), removed=len(removals))

    @staticmethod
    def _ensure_favorite(connection: Connection, artwork_id: int, now: str) -> None:
        exists = connection.scalar(
            select(favorite_artworks.c.artwork_id).where(favorite_artworks.c.artwork_id == artwork_id)
        )
        if exists is None:
            connection.execute(insert(favorite_artworks).values(artwork_id=artwork_id, created_at=now, updated_at=now))
        else:
            connection.execute(
                update(favorite_artworks).where(favorite_artworks.c.artwork_id == artwork_id).values(updated_at=now)
            )

    @staticmethod
    def _require_artwork(connection: Connection, artwork_id: int) -> None:
        exists = connection.scalar(select(artworks.c.id).where(artworks.c.id == artwork_id))
        if exists is None:
            raise NotFoundError(f"未找到作品，ID: {artwork_id}。")

    @staticmethod
    def _state(connection: Connection, artwork_id: int) -> FavoriteState:
        is_favorite = (
            connection.scalar(
                select(favorite_artworks.c.artwork_id).where(favorite_artworks.c.artwork_id == artwork_id)
            )
            is not None
        )
        return FavoriteState(artwork_id=artwork_id, is_favorite=is_favorite)
