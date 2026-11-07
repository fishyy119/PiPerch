from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import bindparam, delete, insert, select, update

from piperch.database.tables import artworks, favorite_artworks
from piperch.domain.favorites import FavoriteState, FavoriteSyncDiff, FavoriteSyncResult
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
                self.ensure_favorite(connection, artwork_id, now)
            else:
                connection.execute(delete(favorite_artworks).where(favorite_artworks.c.artwork_id == artwork_id))
            return self._state(connection, artwork_id)

    def compare_with_remote(self, remote_artwork_ids: Sequence[int]) -> FavoriteSyncDiff:
        remote_ids = set(remote_artwork_ids)
        with self._database.connect() as connection:
            local_by_remote = {
                int(remote_id): int(local_id)
                for remote_id, local_id in connection.execute(
                    select(artworks.c.remote_id, artworks.c.id).where(artworks.c.source == "pixiv")
                )
            }
            local_ids = set(local_by_remote.values())
            local_favorite_ids = set(connection.scalars(select(favorite_artworks.c.artwork_id))) & local_ids
        matched_favorite_ids = {local_by_remote[remote_id] for remote_id in remote_ids & local_by_remote.keys()}
        return FavoriteSyncDiff(
            pixiv_favorite_count=len(remote_ids),
            local_artwork_count=len(local_ids),
            local_favorite_count=len(local_favorite_ids),
            matched_favorite_count=len(matched_favorite_ids),
            unavailable_locally_count=len(remote_ids - local_by_remote.keys()),
            add_artwork_ids=tuple(sorted(matched_favorite_ids - local_favorite_ids)),
            remove_artwork_ids=tuple(sorted(local_favorite_ids - matched_favorite_ids)),
        )

    def remote_ids_for_local(self, artwork_ids: Sequence[int]) -> dict[int, int]:
        output: dict[int, int] = {}
        unique_ids = tuple(dict.fromkeys(artwork_ids))
        with self._database.connect() as connection:
            for start in range(0, len(unique_ids), 900):
                rows = connection.execute(
                    select(artworks.c.id, artworks.c.remote_id).where(
                        artworks.c.source == "pixiv", artworks.c.id.in_(unique_ids[start : start + 900])
                    )
                )
                output.update((int(local_id), int(remote_id)) for local_id, remote_id in rows)
        return output

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
            local_ids = set(connection.scalars(select(artworks.c.id).where(artworks.c.source == "pixiv")))
            local_favorite_ids = set(connection.scalars(select(favorite_artworks.c.artwork_id))) & local_ids
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
    def ensure_favorite(connection: Connection, artwork_id: int, now: str) -> None:
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
