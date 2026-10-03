from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from piperch.database.tables import (
    artworks,
    favorite_artworks,
    favorite_group_items,
    favorite_groups,
)
from piperch.domain import FavoriteGroup, FavoriteState
from piperch.errors import AppError, ConflictError, NotFoundError
from piperch.repositories._rows import integer as _integer
from piperch.repositories._rows import string as _string
from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine import Connection

    from piperch.database import Database


MAX_FAVORITE_GROUPS = 10


def normalize_favorite_group_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise AppError("invalid_favorite_group_name", "收藏分组名称不能为空。")
    if len(name) > 20:
        raise AppError("invalid_favorite_group_name", "收藏分组名称不能超过 20 个字符。")
    if any(character.isspace() for character in name):
        raise AppError("invalid_favorite_group_name", "收藏分组名称不能包含空白字符。")
    return name


def validate_imported_favorite_groups(values: Sequence[str]) -> tuple[str, ...]:
    groups = tuple(dict.fromkeys(values))
    if len(groups) > MAX_FAVORITE_GROUPS:
        raise AppError("invalid_remote_bookmark_tags", "Pixiv 收藏标签超过本地允许的 10 个分组。")
    for group in groups:
        if normalize_favorite_group_name(group) != group:
            raise AppError("invalid_remote_bookmark_tags", "Pixiv 收藏标签不满足本地分组名称约束。")
    return groups


class FavoriteRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_groups(self) -> list[FavoriteGroup]:
        statement = (
            select(
                favorite_groups.c.id,
                favorite_groups.c.name,
                func.count(favorite_group_items.c.artwork_id).label("artwork_count"),
            )
            .select_from(
                favorite_groups.outerjoin(
                    favorite_group_items,
                    favorite_groups.c.id == favorite_group_items.c.group_id,
                )
            )
            .group_by(favorite_groups.c.id)
            .order_by(favorite_groups.c.id.asc())
        )
        with self._database.connect() as connection:
            return [
                FavoriteGroup(
                    group_id=_integer(row["id"]),
                    name=_string(row["name"]),
                    artwork_count=_integer(row["artwork_count"]),
                )
                for row in connection.execute(statement).mappings()
            ]

    def create_group(self, name: str) -> FavoriteGroup:
        normalized = normalize_favorite_group_name(name)
        now = utc_now_text()
        try:
            with self._database.begin() as connection:
                result = connection.execute(
                    insert(favorite_groups).values(name=normalized, created_at=now, updated_at=now)
                )
                group_id = int(result.inserted_primary_key[0])
        except IntegrityError as error:
            raise ConflictError("favorite_group_exists", "同名收藏分组已经存在。") from error
        return FavoriteGroup(group_id=group_id, name=normalized, artwork_count=0)

    def rename_group(self, group_id: int, name: str) -> FavoriteGroup:
        normalized = normalize_favorite_group_name(name)
        now = utc_now_text()
        try:
            with self._database.begin() as connection:
                result = connection.execute(
                    update(favorite_groups)
                    .where(favorite_groups.c.id == group_id)
                    .values(name=normalized, updated_at=now)
                )
                if not result.rowcount:
                    raise NotFoundError("未找到该收藏分组。")
                count = int(
                    connection.scalar(select(func.count()).where(favorite_group_items.c.group_id == group_id)) or 0
                )
        except IntegrityError as error:
            raise ConflictError("favorite_group_exists", "同名收藏分组已经存在。") from error
        return FavoriteGroup(group_id=group_id, name=normalized, artwork_count=count)

    def delete_group(self, group_id: int) -> None:
        with self._database.begin() as connection:
            result = connection.execute(delete(favorite_groups).where(favorite_groups.c.id == group_id))
            if not result.rowcount:
                raise NotFoundError("未找到该收藏分组。")

    def get_state(self, artwork_id: int) -> FavoriteState:
        with self._database.connect() as connection:
            self._require_artworks(connection, (artwork_id,))
            return self._state(connection, artwork_id)

    def replace_state(
        self,
        artwork_id: int,
        *,
        is_favorite: bool,
        group_ids: Sequence[int],
    ) -> FavoriteState:
        unique_group_ids = tuple(dict.fromkeys(group_ids))
        if not is_favorite and unique_group_ids:
            raise AppError("invalid_favorite_state", "取消收藏时不能保留收藏分组。")
        if len(unique_group_ids) > MAX_FAVORITE_GROUPS:
            raise AppError("favorite_group_limit", "每件收藏最多属于 10 个分组。")
        now = utc_now_text()
        with self._database.begin() as connection:
            self._require_artworks(connection, (artwork_id,))
            self._require_groups(connection, unique_group_ids)
            if not is_favorite:
                connection.execute(delete(favorite_artworks).where(favorite_artworks.c.artwork_id == artwork_id))
            else:
                self._ensure_favorite(connection, artwork_id, now)
                connection.execute(delete(favorite_group_items).where(favorite_group_items.c.artwork_id == artwork_id))
                if unique_group_ids:
                    connection.execute(
                        insert(favorite_group_items),
                        [{"artwork_id": artwork_id, "group_id": group_id} for group_id in unique_group_ids],
                    )
            return self._state(connection, artwork_id)

    def bulk_set_favorite(self, artwork_ids: Sequence[int], *, is_favorite: bool) -> None:
        unique_artwork_ids = tuple(dict.fromkeys(artwork_ids))
        now = utc_now_text()
        with self._database.begin() as connection:
            self._require_artworks(connection, unique_artwork_ids)
            if not is_favorite:
                connection.execute(
                    delete(favorite_artworks).where(favorite_artworks.c.artwork_id.in_(unique_artwork_ids))
                )
                return
            existing = set(
                connection.scalars(
                    select(favorite_artworks.c.artwork_id).where(favorite_artworks.c.artwork_id.in_(unique_artwork_ids))
                )
            )
            missing = [artwork_id for artwork_id in unique_artwork_ids if artwork_id not in existing]
            if missing:
                connection.execute(
                    insert(favorite_artworks),
                    [{"artwork_id": artwork_id, "created_at": now, "updated_at": now} for artwork_id in missing],
                )

    def bulk_update_groups(
        self,
        artwork_ids: Sequence[int],
        *,
        add_group_ids: Sequence[int],
        remove_group_ids: Sequence[int],
    ) -> None:
        unique_artwork_ids = tuple(dict.fromkeys(artwork_ids))
        add_ids = tuple(dict.fromkeys(add_group_ids))
        remove_ids = tuple(dict.fromkeys(remove_group_ids))
        if set(add_ids) & set(remove_ids):
            raise AppError("invalid_favorite_group_change", "同一分组不能同时添加和移除。")
        now = utc_now_text()
        with self._database.begin() as connection:
            self._require_artworks(connection, unique_artwork_ids)
            self._require_groups(connection, (*add_ids, *remove_ids))
            existing_rows = connection.execute(
                select(favorite_group_items.c.artwork_id, favorite_group_items.c.group_id).where(
                    favorite_group_items.c.artwork_id.in_(unique_artwork_ids)
                )
            )
            current: dict[int, set[int]] = {artwork_id: set() for artwork_id in unique_artwork_ids}
            for artwork_id, group_id in existing_rows:
                current[int(artwork_id)].add(int(group_id))
            final_groups = {
                artwork_id: (groups | set(add_ids)) - set(remove_ids) for artwork_id, groups in current.items()
            }
            if any(len(groups) > MAX_FAVORITE_GROUPS for groups in final_groups.values()):
                raise AppError("favorite_group_limit", "每件收藏最多属于 10 个分组。")

            if add_ids:
                existing_favorites = set(
                    connection.scalars(
                        select(favorite_artworks.c.artwork_id).where(
                            favorite_artworks.c.artwork_id.in_(unique_artwork_ids)
                        )
                    )
                )
                missing_favorites = [
                    artwork_id for artwork_id in unique_artwork_ids if artwork_id not in existing_favorites
                ]
                if missing_favorites:
                    connection.execute(
                        insert(favorite_artworks),
                        [
                            {"artwork_id": artwork_id, "created_at": now, "updated_at": now}
                            for artwork_id in missing_favorites
                        ],
                    )

            connection.execute(
                delete(favorite_group_items).where(favorite_group_items.c.artwork_id.in_(unique_artwork_ids))
            )
            rows = [
                {"artwork_id": artwork_id, "group_id": group_id}
                for artwork_id, group_ids in final_groups.items()
                for group_id in sorted(group_ids)
            ]
            if rows:
                connection.execute(insert(favorite_group_items), rows)

    @staticmethod
    def import_public_bookmark(
        connection: Connection,
        artwork_id: int,
        group_names: Sequence[str],
        now: str,
    ) -> None:
        connection.execute(insert(favorite_artworks).values(artwork_id=artwork_id, created_at=now, updated_at=now))
        for name in group_names:
            group_id = connection.scalar(select(favorite_groups.c.id).where(favorite_groups.c.name == name))
            if group_id is None:
                result = connection.execute(insert(favorite_groups).values(name=name, created_at=now, updated_at=now))
                group_id = int(result.inserted_primary_key[0])
            connection.execute(insert(favorite_group_items).values(artwork_id=artwork_id, group_id=group_id))

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
    def _require_artworks(connection: Connection, artwork_ids: Sequence[int]) -> None:
        if not artwork_ids:
            raise AppError("empty_artwork_selection", "至少需要选择一件作品。")
        existing = set(connection.scalars(select(artworks.c.id).where(artworks.c.id.in_(artwork_ids))))
        missing = [artwork_id for artwork_id in artwork_ids if artwork_id not in existing]
        if missing:
            raise NotFoundError(f"未找到作品，ID: {', '.join(str(item) for item in missing)}。")

    @staticmethod
    def _require_groups(connection: Connection, group_ids: Sequence[int]) -> None:
        if not group_ids:
            return
        existing = set(connection.scalars(select(favorite_groups.c.id).where(favorite_groups.c.id.in_(group_ids))))
        missing = [group_id for group_id in group_ids if group_id not in existing]
        if missing:
            raise NotFoundError(f"未找到收藏分组，ID: {', '.join(str(item) for item in missing)}。")

    @staticmethod
    def _state(connection: Connection, artwork_id: int) -> FavoriteState:
        is_favorite = (
            connection.scalar(
                select(favorite_artworks.c.artwork_id).where(favorite_artworks.c.artwork_id == artwork_id)
            )
            is not None
        )
        rows = connection.execute(
            select(favorite_groups.c.id, favorite_groups.c.name)
            .select_from(
                favorite_group_items.join(
                    favorite_groups,
                    favorite_group_items.c.group_id == favorite_groups.c.id,
                )
            )
            .where(favorite_group_items.c.artwork_id == artwork_id)
            .order_by(favorite_groups.c.id.asc())
        ).mappings()
        groups = [(_integer(row["id"]), _string(row["name"])) for row in rows]
        return FavoriteState(
            artwork_id=artwork_id,
            is_favorite=is_favorite,
            group_ids=tuple(group_id for group_id, _ in groups),
            group_names=tuple(name for _, name in groups),
        )
