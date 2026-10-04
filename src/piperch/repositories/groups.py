from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from piperch.database.tables import artwork_group_items, artwork_groups, artworks
from piperch.domain import ArtworkGroup, ArtworkGroupMembership
from piperch.errors import AppError, ConflictError, NotFoundError
from piperch.repositories._rows import integer as _integer
from piperch.repositories._rows import string as _string
from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine import Connection

    from piperch.database import Database


MAX_ARTWORK_GROUPS = 10


def normalize_group_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise AppError("invalid_group_name", "本地分组名称不能为空。")
    if len(name) > 20:
        raise AppError("invalid_group_name", "本地分组名称不能超过 20 个字符。")
    if any(character.isspace() for character in name):
        raise AppError("invalid_group_name", "本地分组名称不能包含空白字符。")
    return name


def validate_imported_group_names(values: Sequence[str]) -> tuple[str, ...]:
    groups = tuple(dict.fromkeys(values))
    if len(groups) > MAX_ARTWORK_GROUPS:
        raise AppError("invalid_remote_bookmark_tags", "Pixiv 收藏标签超过本地允许的 10 个分组。")
    for group in groups:
        if normalize_group_name(group) != group:
            raise AppError("invalid_remote_bookmark_tags", "Pixiv 收藏标签不满足本地分组名称约束。")
    return groups


class ArtworkGroupRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_groups(self) -> list[ArtworkGroup]:
        statement = (
            select(
                artwork_groups.c.id,
                artwork_groups.c.name,
                func.count(artwork_group_items.c.artwork_id).label("artwork_count"),
            )
            .select_from(
                artwork_groups.outerjoin(
                    artwork_group_items,
                    artwork_groups.c.id == artwork_group_items.c.group_id,
                )
            )
            .group_by(artwork_groups.c.id)
            .order_by(artwork_groups.c.name.asc(), artwork_groups.c.id.asc())
        )
        with self._database.connect() as connection:
            return [
                ArtworkGroup(
                    group_id=_integer(row["id"]),
                    name=_string(row["name"]),
                    artwork_count=_integer(row["artwork_count"]),
                )
                for row in connection.execute(statement).mappings()
            ]

    def create_group(self, name: str) -> ArtworkGroup:
        normalized = normalize_group_name(name)
        now = utc_now_text()
        try:
            with self._database.begin() as connection:
                result = connection.execute(
                    insert(artwork_groups).values(name=normalized, created_at=now, updated_at=now)
                )
                inserted_primary_key = result.inserted_primary_key
                if inserted_primary_key is None:
                    raise RuntimeError("数据库未返回新建本地分组的 ID。")
                group_id = _integer(cast("object", inserted_primary_key[0]))
        except IntegrityError as error:
            raise ConflictError("group_exists", "同名本地分组已经存在。") from error
        return ArtworkGroup(group_id=group_id, name=normalized, artwork_count=0)

    def rename_group(self, group_id: int, name: str) -> ArtworkGroup:
        normalized = normalize_group_name(name)
        now = utc_now_text()
        try:
            with self._database.begin() as connection:
                result = connection.execute(
                    update(artwork_groups)
                    .where(artwork_groups.c.id == group_id)
                    .values(name=normalized, updated_at=now)
                )
                if not result.rowcount:
                    raise NotFoundError("未找到该本地分组。")
                count = int(
                    connection.scalar(select(func.count()).where(artwork_group_items.c.group_id == group_id)) or 0
                )
        except IntegrityError as error:
            raise ConflictError("group_exists", "同名本地分组已经存在。") from error
        return ArtworkGroup(group_id=group_id, name=normalized, artwork_count=count)

    def delete_group(self, group_id: int) -> None:
        with self._database.begin() as connection:
            result = connection.execute(delete(artwork_groups).where(artwork_groups.c.id == group_id))
            if not result.rowcount:
                raise NotFoundError("未找到该本地分组。")

    def replace_groups(self, artwork_id: int, *, group_ids: Sequence[int]) -> ArtworkGroupMembership:
        unique_group_ids = tuple(dict.fromkeys(group_ids))
        if len(unique_group_ids) > MAX_ARTWORK_GROUPS:
            raise AppError("group_limit", "每件作品最多属于 10 个本地分组。")
        with self._database.begin() as connection:
            self._require_artworks(connection, (artwork_id,))
            self._require_groups(connection, unique_group_ids)
            self._replace_group_items(connection, artwork_id, unique_group_ids)
            return self._membership(connection, artwork_id)

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
            raise AppError("invalid_group_change", "同一分组不能同时添加和移除。")
        with self._database.begin() as connection:
            self._require_artworks(connection, unique_artwork_ids)
            self._require_groups(connection, (*add_ids, *remove_ids))
            existing_rows = connection.execute(
                select(artwork_group_items.c.artwork_id, artwork_group_items.c.group_id).where(
                    artwork_group_items.c.artwork_id.in_(unique_artwork_ids)
                )
            )
            current: dict[int, set[int]] = {artwork_id: set() for artwork_id in unique_artwork_ids}
            for artwork_id, group_id in existing_rows:
                current[int(artwork_id)].add(int(group_id))
            final_groups = {
                artwork_id: (groups | set(add_ids)) - set(remove_ids) for artwork_id, groups in current.items()
            }
            if any(len(groups) > MAX_ARTWORK_GROUPS for groups in final_groups.values()):
                raise AppError("group_limit", "每件作品最多属于 10 个本地分组。")

            changed_ids = [artwork_id for artwork_id, groups in final_groups.items() if groups != current[artwork_id]]
            if not changed_ids:
                return
            connection.execute(delete(artwork_group_items).where(artwork_group_items.c.artwork_id.in_(changed_ids)))
            rows = [
                {"artwork_id": artwork_id, "group_id": group_id}
                for artwork_id in changed_ids
                for group_id in sorted(final_groups[artwork_id])
            ]
            if rows:
                connection.execute(insert(artwork_group_items), rows)

    @staticmethod
    def import_bookmark_groups(
        connection: Connection,
        artwork_id: int,
        group_names: Sequence[str],
        now: str,
    ) -> None:
        for name in group_names:
            group_id = connection.scalar(select(artwork_groups.c.id).where(artwork_groups.c.name == name))
            if group_id is None:
                result = connection.execute(insert(artwork_groups).values(name=name, created_at=now, updated_at=now))
                inserted_primary_key = result.inserted_primary_key
                if inserted_primary_key is None:
                    raise RuntimeError("数据库未返回新建本地分组的 ID。")
                group_id = _integer(cast("object", inserted_primary_key[0]))
            connection.execute(insert(artwork_group_items).values(artwork_id=artwork_id, group_id=group_id))

    @staticmethod
    def _replace_group_items(connection: Connection, artwork_id: int, group_ids: Sequence[int]) -> None:
        connection.execute(delete(artwork_group_items).where(artwork_group_items.c.artwork_id == artwork_id))
        if group_ids:
            connection.execute(
                insert(artwork_group_items),
                [{"artwork_id": artwork_id, "group_id": group_id} for group_id in group_ids],
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
        existing = set(connection.scalars(select(artwork_groups.c.id).where(artwork_groups.c.id.in_(group_ids))))
        missing = [group_id for group_id in group_ids if group_id not in existing]
        if missing:
            raise NotFoundError(f"未找到本地分组，ID: {', '.join(str(item) for item in missing)}。")

    @staticmethod
    def _membership(connection: Connection, artwork_id: int) -> ArtworkGroupMembership:
        rows = connection.execute(
            select(artwork_groups.c.id)
            .select_from(
                artwork_group_items.join(
                    artwork_groups,
                    artwork_group_items.c.group_id == artwork_groups.c.id,
                )
            )
            .where(artwork_group_items.c.artwork_id == artwork_id)
            .order_by(artwork_groups.c.id.asc())
        ).mappings()
        return ArtworkGroupMembership(
            artwork_id=artwork_id,
            group_ids=tuple(_integer(row["id"]) for row in rows),
        )
