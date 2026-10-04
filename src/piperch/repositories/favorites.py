from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update

from piperch.database.tables import artworks, favorite_artworks
from piperch.domain import FavoriteState
from piperch.errors import NotFoundError
from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
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
