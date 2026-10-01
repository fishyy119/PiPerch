# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# SQLAlchemy Core 的泛型表达式会丢失部分列类型，此文件在数据库边界精确关闭相关噪音。
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from sqlalchemy import Select, and_, case, delete, func, insert, literal, or_, select, update

from piperch.database.tables import (
    artwork_tags,
    artworks,
    authors,
    media_files,
    series,
    tags,
    ugoira_frames,
)
from piperch.domain import (
    ArtworkDetail,
    ArtworkSummary,
    ArtworkType,
    MediaRecord,
    NamedCount,
    RemoteArtwork,
    TagRecord,
    UgoiraFrame,
)
from piperch.errors import NotFoundError
from piperch.repositories._rows import (
    integer as _integer,
)
from piperch.repositories._rows import (
    optional_integer as _optional_integer,
)
from piperch.repositories._rows import (
    optional_string as _optional_string,
)
from piperch.repositories._rows import (
    string as _string,
)
from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from sqlalchemy.engine import RowMapping

    from piperch.database import Database


class ArtworkRepository:
    _SORT_COLUMNS: ClassVar[dict[str, object]] = {
        "downloadedAt": artworks.c.downloaded_at,
        "publishedAt": artworks.c.published_at,
        "title": artworks.c.title,
        "id": artworks.c.id,
    }

    def __init__(self, database: Database) -> None:
        self._database = database

    def find_existing_ids(self, artwork_ids: Sequence[int]) -> set[int]:
        """返回已经保存到本地图库的作品 ID。"""
        unique_ids = tuple(dict.fromkeys(artwork_ids))
        if not unique_ids:
            return set()
        existing_ids: set[int] = set()
        with self._database.connect() as connection:
            for start in range(0, len(unique_ids), 900):
                batch = unique_ids[start : start + 900]
                rows = connection.scalars(select(artworks.c.id).where(artworks.c.id.in_(batch)))
                existing_ids.update(int(artwork_id) for artwork_id in rows)
        return existing_ids

    def is_complete(self, artwork_id: int, library_root: Path) -> bool:
        with self._database.connect() as connection:
            artwork = connection.execute(
                select(artworks.c.artwork_type, artworks.c.page_count).where(artworks.c.id == artwork_id)
            ).first()
            media = connection.execute(
                select(
                    media_files.c.role,
                    media_files.c.page_index,
                    media_files.c.relative_path,
                    media_files.c.byte_size,
                ).where(media_files.c.artwork_id == artwork_id)
            ).all()
        if artwork is None or not media:
            return False
        artwork_type = ArtworkType(cast("str", artwork.artwork_type))
        if artwork_type is ArtworkType.UGOIRA:
            roles = {cast("str", row.role) for row in media}
            if not {"cover", "ugoiraZip", "ugoiraMetadata"} <= roles:
                return False
        else:
            page_indices = {
                cast("int", row.page_index) for row in media if row.role == "page" and row.page_index is not None
            }
            if page_indices != set(range(cast("int", artwork.page_count))):
                return False
        return all(
            (path := library_root / cast("str", row.relative_path)).is_file()
            and path.stat().st_size == cast("int", row.byte_size)
            for row in media
        )

    def list_media(self, artwork_id: int) -> tuple[MediaRecord, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(select(media_files).where(media_files.c.artwork_id == artwork_id)).mappings()
            return tuple(
                MediaRecord(
                    role=_string(row["role"]),
                    page_index=_optional_integer(row["page_index"]),
                    relative_path=_string(row["relative_path"]),
                    mime_type=_string(row["mime_type"]),
                    byte_size=_integer(row["byte_size"]),
                )
                for row in rows
            )

    def save_download(
        self,
        artwork: RemoteArtwork,
        media: Sequence[MediaRecord],
    ) -> None:
        now = utc_now_text()
        with self._database.begin() as connection:
            self._upsert_author(connection, artwork, now)
            self._upsert_series(connection, artwork, now)
            existing_downloaded_at = connection.scalar(
                select(artworks.c.downloaded_at).where(artworks.c.id == artwork.artwork_id)
            )
            values = {
                "id": artwork.artwork_id,
                "artwork_type": artwork.artwork_type.value,
                "title": artwork.title,
                "description": artwork.description,
                "author_id": artwork.author_id,
                "series_id": artwork.series_id,
                "page_count": artwork.page_count,
                "width": artwork.width,
                "height": artwork.height,
                "x_restrict": artwork.x_restrict,
                "is_ai": artwork.is_ai,
                "published_at": artwork.published_at,
                "downloaded_at": existing_downloaded_at or now,
                "metadata_updated_at": now,
            }
            if existing_downloaded_at is None:
                connection.execute(insert(artworks).values(**values))
            else:
                connection.execute(update(artworks).where(artworks.c.id == artwork.artwork_id).values(**values))

            connection.execute(delete(artwork_tags).where(artwork_tags.c.artwork_id == artwork.artwork_id))
            for tag in artwork.tags:
                tag_id = connection.scalar(select(tags.c.id).where(tags.c.name == tag.name))
                if tag_id is None:
                    connection.execute(insert(tags).values(name=tag.name, translated_name=tag.translated_name))
                    tag_id = connection.scalar(select(tags.c.id).where(tags.c.name == tag.name))
                    if tag_id is None:
                        raise RuntimeError("写入标签后未能读取主键。")
                elif tag.translated_name:
                    connection.execute(
                        update(tags).where(tags.c.id == tag_id).values(translated_name=tag.translated_name)
                    )
                connection.execute(insert(artwork_tags).values(artwork_id=artwork.artwork_id, tag_id=tag_id))

            connection.execute(delete(media_files).where(media_files.c.artwork_id == artwork.artwork_id))
            if media:
                connection.execute(
                    insert(media_files),
                    [
                        {
                            "artwork_id": artwork.artwork_id,
                            "role": item.role,
                            "page_index": item.page_index,
                            "relative_path": item.relative_path,
                            "mime_type": item.mime_type,
                            "byte_size": item.byte_size,
                            "downloaded_at": now,
                        }
                        for item in media
                    ],
                )

            connection.execute(delete(ugoira_frames).where(ugoira_frames.c.artwork_id == artwork.artwork_id))
            if artwork.ugoira_frames:
                connection.execute(
                    insert(ugoira_frames),
                    [
                        {
                            "artwork_id": artwork.artwork_id,
                            "sequence": index,
                            "file_name": frame.file_name,
                            "delay_ms": frame.delay_ms,
                        }
                        for index, frame in enumerate(artwork.ugoira_frames)
                    ],
                )

    @staticmethod
    def _upsert_author(connection: object, artwork: RemoteArtwork, now: str) -> None:
        values = {
            "id": artwork.author_id,
            "name": artwork.author_name,
            "account": artwork.author_account,
            "avatar_url": artwork.author_avatar_url,
            "updated_at": now,
        }
        exists = connection.scalar(select(authors.c.id).where(authors.c.id == artwork.author_id))
        if exists is None:
            connection.execute(insert(authors).values(**values))
        else:
            connection.execute(update(authors).where(authors.c.id == artwork.author_id).values(**values))

    @staticmethod
    def _upsert_series(connection: object, artwork: RemoteArtwork, now: str) -> None:
        if artwork.series_id is None or artwork.series_title is None:
            return
        values = {
            "id": artwork.series_id,
            "title": artwork.series_title,
            "author_id": artwork.author_id,
            "updated_at": now,
        }
        exists = connection.scalar(select(series.c.id).where(series.c.id == artwork.series_id))
        if exists is None:
            connection.execute(insert(series).values(**values))
        else:
            connection.execute(update(series).where(series.c.id == artwork.series_id).values(**values))

    def list_artworks(
        self,
        *,
        page: int,
        size: int,
        search: str,
        tag_ids: Sequence[int],
        author_id: int | None,
        series_id: int | None,
        artwork_type: ArtworkType | None,
        rating: str,
        ai: str,
        sort: str,
        order: str,
    ) -> tuple[list[ArtworkSummary], int]:
        conditions = []
        if search:
            search_value = search.strip()
            text_match = or_(
                artworks.c.title.contains(search_value, autoescape=True),
                authors.c.name.contains(search_value, autoescape=True),
            )
            conditions.append(
                or_(artworks.c.id == int(search_value), text_match) if search_value.isdigit() else text_match
            )
        if author_id is not None:
            conditions.append(artworks.c.author_id == author_id)
        if series_id is not None:
            conditions.append(artworks.c.series_id == series_id)
        if artwork_type is not None:
            conditions.append(artworks.c.artwork_type == artwork_type.value)
        if rating == "safe":
            conditions.append(artworks.c.x_restrict == 0)
        elif rating == "r18":
            conditions.append(artworks.c.x_restrict > 0)
        if ai == "yes":
            conditions.append(artworks.c.is_ai.is_(True))
        elif ai == "no":
            conditions.append(artworks.c.is_ai.is_(False))
        if tag_ids:
            matching_tags = (
                select(artwork_tags.c.artwork_id)
                .where(artwork_tags.c.tag_id.in_(tag_ids))
                .group_by(artwork_tags.c.artwork_id)
                .having(func.count(func.distinct(artwork_tags.c.tag_id)) == len(set(tag_ids)))
            )
            conditions.append(artworks.c.id.in_(matching_tags))

        base = artworks.join(authors, artworks.c.author_id == authors.c.id).outerjoin(
            series, artworks.c.series_id == series.c.id
        )
        count_statement = select(func.count()).select_from(base)
        statement: Select[tuple[object, ...]] = select(
            artworks,
            authors.c.name.label("author_name"),
            series.c.title.label("series_title"),
        ).select_from(base)
        if conditions:
            count_statement = count_statement.where(and_(*conditions))
            statement = statement.where(and_(*conditions))
        sort_column = self._SORT_COLUMNS.get(sort, artworks.c.downloaded_at)
        direction = sort_column.asc() if order == "asc" else sort_column.desc()
        statement = statement.order_by(direction, artworks.c.id.desc()).offset(page * size).limit(size)

        with self._database.connect() as connection:
            total = int(connection.scalar(count_statement) or 0)
            rows = connection.execute(statement).mappings().all()
            summaries = [self._summary_from_row(row) for row in rows]
        return summaries, total

    def list_related_artworks(self, artwork_id: int, limit: int) -> list[ArtworkSummary]:
        """按同作者和共享标签的加权分数返回本地相关作品。"""
        with self._database.connect() as connection:
            target_author_id = connection.scalar(select(artworks.c.author_id).where(artworks.c.id == artwork_id))
            if target_author_id is None:
                raise NotFoundError("未找到该作品。")
            target_tag_ids = tuple(
                connection.scalars(select(artwork_tags.c.tag_id).where(artwork_tags.c.artwork_id == artwork_id))
            )

            author_score = case(
                (artworks.c.author_id == target_author_id, 10),
                else_=0,
            )
            if target_tag_ids:
                shared_tag_count = func.count(
                    func.distinct(
                        case(
                            (
                                artwork_tags.c.tag_id.in_(target_tag_ids),
                                artwork_tags.c.tag_id,
                            ),
                            else_=None,
                        )
                    )
                )
                candidate_condition = or_(
                    artworks.c.author_id == target_author_id,
                    artwork_tags.c.tag_id.in_(target_tag_ids),
                )
            else:
                shared_tag_count = literal(0)
                candidate_condition = artworks.c.author_id == target_author_id

            candidate_scores = (
                select(
                    artworks.c.id.label("artwork_id"),
                    (author_score + shared_tag_count * 2).label("score"),
                )
                .select_from(
                    artworks.outerjoin(
                        artwork_tags,
                        artworks.c.id == artwork_tags.c.artwork_id,
                    )
                )
                .where(artworks.c.id != artwork_id, candidate_condition)
                .group_by(artworks.c.id)
                .subquery()
            )
            base = (
                candidate_scores.join(
                    artworks,
                    candidate_scores.c.artwork_id == artworks.c.id,
                )
                .join(authors, artworks.c.author_id == authors.c.id)
                .outerjoin(series, artworks.c.series_id == series.c.id)
            )
            statement: Select[tuple[object, ...]] = (
                select(
                    artworks,
                    authors.c.name.label("author_name"),
                    series.c.title.label("series_title"),
                )
                .select_from(base)
                .order_by(
                    candidate_scores.c.score.desc(),
                    artworks.c.downloaded_at.desc(),
                    artworks.c.id.desc(),
                )
                .limit(limit)
            )
            rows = connection.execute(statement).mappings().all()
            summaries = [self._summary_from_row(row) for row in rows]
        return summaries

    def get_detail(self, artwork_id: int) -> ArtworkDetail:
        base = artworks.join(authors, artworks.c.author_id == authors.c.id).outerjoin(
            series, artworks.c.series_id == series.c.id
        )
        statement = (
            select(
                artworks,
                authors.c.name.label("author_name"),
                series.c.title.label("series_title"),
            )
            .select_from(base)
            .where(artworks.c.id == artwork_id)
        )
        with self._database.connect() as connection:
            row = connection.execute(statement).mappings().first()
            if row is None:
                raise NotFoundError("未找到该作品。")
            summary = self._summary_from_row(row)
            self._attach_tags(connection, [summary])
            media_rows = connection.execute(
                select(media_files)
                .where(media_files.c.artwork_id == artwork_id)
                .order_by(media_files.c.page_index.asc())
            ).mappings()
            frame_rows = connection.execute(
                select(ugoira_frames)
                .where(ugoira_frames.c.artwork_id == artwork_id)
                .order_by(ugoira_frames.c.sequence.asc())
            ).mappings()
            return ArtworkDetail(
                summary=summary,
                description=_string(row["description"]),
                width=_optional_integer(row["width"]),
                height=_optional_integer(row["height"]),
                media=tuple(
                    MediaRecord(
                        role=_string(item["role"]),
                        page_index=_optional_integer(item["page_index"]),
                        relative_path=_string(item["relative_path"]),
                        mime_type=_string(item["mime_type"]),
                        byte_size=_integer(item["byte_size"]),
                    )
                    for item in media_rows
                ),
                ugoira_frames=tuple(
                    UgoiraFrame(
                        file_name=_string(item["file_name"]),
                        delay_ms=_integer(item["delay_ms"]),
                    )
                    for item in frame_rows
                ),
            )

    def get_media(self, artwork_id: int, role: str, page_index: int | None) -> MediaRecord:
        condition = and_(
            media_files.c.artwork_id == artwork_id,
            media_files.c.role == role,
            media_files.c.page_index.is_(None) if page_index is None else media_files.c.page_index == page_index,
        )
        with self._database.connect() as connection:
            row = connection.execute(select(media_files).where(condition)).mappings().first()
        if row is None:
            raise NotFoundError("未找到对应的本地媒体文件。")
        return MediaRecord(
            role=_string(row["role"]),
            page_index=_optional_integer(row["page_index"]),
            relative_path=_string(row["relative_path"]),
            mime_type=_string(row["mime_type"]),
            byte_size=_integer(row["byte_size"]),
        )

    def list_tags(self, search: str, limit: int) -> list[tuple[int, TagRecord, int]]:
        statement = (
            select(
                tags.c.id,
                tags.c.name,
                tags.c.translated_name,
                func.count(artwork_tags.c.artwork_id).label("artwork_count"),
            )
            .select_from(tags.join(artwork_tags, tags.c.id == artwork_tags.c.tag_id))
            .group_by(tags.c.id)
            .order_by(func.count(artwork_tags.c.artwork_id).desc(), tags.c.name.asc())
            .limit(limit)
        )
        if search:
            statement = statement.where(
                or_(
                    tags.c.name.contains(search, autoescape=True),
                    tags.c.translated_name.contains(search, autoescape=True),
                )
            )
        with self._database.connect() as connection:
            rows = connection.execute(statement).mappings()
            return [
                (
                    _integer(row["id"]),
                    TagRecord(_string(row["name"]), _optional_string(row["translated_name"])),
                    _integer(row["artwork_count"]),
                )
                for row in rows
            ]

    def list_authors(self, page: int, size: int, search: str) -> tuple[list[NamedCount], int]:
        return self._list_named(authors, authors.c.name, authors.c.id, page, size, search)

    def list_series(self, page: int, size: int, search: str) -> tuple[list[NamedCount], int]:
        joined = series.join(artworks, series.c.id == artworks.c.series_id).join(
            authors, series.c.author_id == authors.c.id
        )
        conditions = [series.c.title.contains(search, autoescape=True)] if search else []
        statement = (
            select(
                series.c.id,
                series.c.title.label("name"),
                authors.c.name.label("subtitle"),
                func.count(artworks.c.id).label("item_count"),
            )
            .select_from(joined)
            .group_by(series.c.id, authors.c.name)
            .order_by(series.c.title.asc())
            .offset(page * size)
            .limit(size)
        )
        count_statement = select(func.count(func.distinct(series.c.id))).select_from(joined)
        if conditions:
            statement = statement.where(and_(*conditions))
            count_statement = count_statement.where(and_(*conditions))
        with self._database.connect() as connection:
            total = int(connection.scalar(count_statement) or 0)
            rows = connection.execute(statement).mappings()
            return (
                [
                    NamedCount(
                        item_id=_integer(row["id"]),
                        name=_string(row["name"]),
                        subtitle=_string(row["subtitle"]),
                        count=_integer(row["item_count"]),
                    )
                    for row in rows
                ],
                total,
            )

    def delete_metadata(self, artwork_ids: Sequence[int]) -> int:
        if not artwork_ids:
            return 0
        with self._database.begin() as connection:
            result = connection.execute(delete(artworks).where(artworks.c.id.in_(artwork_ids)))
            connection.execute(
                delete(tags).where(~select(artwork_tags.c.tag_id).where(artwork_tags.c.tag_id == tags.c.id).exists())
            )
            connection.execute(
                delete(series).where(~select(artworks.c.id).where(artworks.c.series_id == series.c.id).exists())
            )
            connection.execute(
                delete(authors).where(~select(artworks.c.id).where(artworks.c.author_id == authors.c.id).exists())
            )
            return max(0, result.rowcount or 0)

    @staticmethod
    def _summary_from_row(row: RowMapping) -> ArtworkSummary:
        return ArtworkSummary(
            artwork_id=_integer(row["id"]),
            title=_string(row["title"]),
            artwork_type=ArtworkType(_string(row["artwork_type"])),
            author_id=_integer(row["author_id"]),
            author_name=_string(row["author_name"]),
            series_id=_optional_integer(row["series_id"]),
            series_title=_optional_string(row["series_title"]),
            page_count=_integer(row["page_count"]),
            x_restrict=_integer(row["x_restrict"]),
            is_ai=bool(row["is_ai"]),
            published_at=_optional_string(row["published_at"]),
            downloaded_at=_string(row["downloaded_at"]),
        )

    @staticmethod
    def _attach_tags(connection: object, summaries: Sequence[ArtworkSummary]) -> None:
        if not summaries:
            return
        by_id = {summary.artwork_id: summary for summary in summaries}
        rows = connection.execute(
            select(
                artwork_tags.c.artwork_id,
                tags.c.id,
                tags.c.name,
                tags.c.translated_name,
            )
            .select_from(artwork_tags.join(tags, artwork_tags.c.tag_id == tags.c.id))
            .where(artwork_tags.c.artwork_id.in_(by_id))
            .order_by(tags.c.name.asc())
        ).mappings()
        grouped: dict[int, list[tuple[int, TagRecord]]] = {key: [] for key in by_id}
        for row in rows:
            grouped[_integer(row["artwork_id"])].append(
                (
                    _integer(row["id"]),
                    TagRecord(_string(row["name"]), _optional_string(row["translated_name"])),
                )
            )
        for summary in summaries:
            object.__setattr__(summary, "tags", tuple(grouped[summary.artwork_id]))

    def _list_named(
        self,
        source: object,
        name_column: object,
        id_column: object,
        page: int,
        size: int,
        search: str,
    ) -> tuple[list[NamedCount], int]:
        joined = source.join(artworks, id_column == artworks.c.author_id)
        condition = name_column.contains(search, autoescape=True) if search else None
        statement = (
            select(
                id_column.label("id"),
                name_column.label("name"),
                func.count(artworks.c.id).label("item_count"),
            )
            .select_from(joined)
            .group_by(id_column, name_column)
            .order_by(name_column.asc())
            .offset(page * size)
            .limit(size)
        )
        count_statement = select(func.count(func.distinct(id_column))).select_from(joined)
        if condition is not None:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        with self._database.connect() as connection:
            total = int(connection.scalar(count_statement) or 0)
            rows = connection.execute(statement).mappings()
            return (
                [
                    NamedCount(
                        item_id=_integer(row["id"]),
                        name=_string(row["name"]),
                        count=_integer(row["item_count"]),
                    )
                    for row in rows
                ],
                total,
            )
