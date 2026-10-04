from __future__ import annotations

import logging
import sqlite3
import unicodedata
from dataclasses import dataclass
from importlib.resources import as_file, files
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from piperch.database.tables import tag_search_cache, tag_search_cache_state, tags

if TYPE_CHECKING:
    from collections.abc import Sequence
    from importlib.resources.abc import Traversable

    from sqlalchemy.engine import Connection

    from piperch.database import Database

logger = logging.getLogger(__name__)

CATALOG_VERSION = "v2026-10-01"
NORMALIZATION_VERSION = 1
_SQLITE_BATCH_SIZE = 900


class TagCatalogError(RuntimeError):
    pass


class TagCatalog:
    def __init__(self, resource: Traversable, version: str) -> None:
        self._resource = resource
        self.version = version

    @classmethod
    def bundled(cls) -> TagCatalog:
        resource = files("piperch").joinpath("resources", "pixiv_tags.sqlite")
        return cls(resource, CATALOG_VERSION)

    def lookup(self, names: Sequence[str]) -> dict[str, str]:
        unique_names = tuple(dict.fromkeys(names))
        try:
            with as_file(self._resource) as path:
                uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
                connection = sqlite3.connect(uri, uri=True)
                try:
                    columns = {row[1] for row in connection.execute("PRAGMA table_info(pixiv_tags)")}
                    if not {"name", "cn_name"} <= columns:
                        raise TagCatalogError("随附标签词典缺少 pixiv_tags.name 或 pixiv_tags.cn_name 字段。")
                    aliases: dict[str, str] = {}
                    for start in range(0, len(unique_names), _SQLITE_BATCH_SIZE):
                        batch = unique_names[start : start + _SQLITE_BATCH_SIZE]
                        placeholders = ",".join("?" for _ in batch)
                        rows = connection.execute(
                            f"SELECT name, cn_name FROM pixiv_tags WHERE name IN ({placeholders})",  # noqa: S608
                            batch,
                        )
                        aliases.update(
                            {
                                name: cn_name
                                for name, cn_name in rows
                                if isinstance(name, str) and isinstance(cn_name, str) and cn_name.strip()
                            }
                        )
                    return aliases
                finally:
                    connection.close()
        except TagCatalogError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise TagCatalogError("无法读取随附标签词典。") from error


@dataclass(frozen=True, slots=True)
class PreparedTagSearch:
    aliases: dict[str, str]
    catalog_available: bool


class TagSearchIndex:
    def __init__(self, database: Database, catalog: TagCatalog | None = None) -> None:
        self._database = database
        self._catalog = catalog or TagCatalog.bundled()

    @staticmethod
    def normalize(text: str) -> str:
        return unicodedata.normalize("NFKC", text.strip())

    def prepare(self, names: Sequence[str]) -> PreparedTagSearch:
        try:
            raw_aliases = self._catalog.lookup(names)
        except TagCatalogError:
            logger.exception("标签词典不可用，本次仅更新原始标签搜索缓存。")
            return PreparedTagSearch({}, False)
        return PreparedTagSearch(
            {name: normalized for name, alias in raw_aliases.items() if (normalized := self.normalize(alias))},
            True,
        )

    def synchronize(self) -> None:
        with self._database.connect() as connection:
            state = connection.execute(
                select(
                    tag_search_cache_state.c.catalog_version,
                    tag_search_cache_state.c.normalization_version,
                ).where(tag_search_cache_state.c.id == 1)
            ).first()
            full_rebuild = (
                state is None
                or state.catalog_version != self._catalog.version
                or state.normalization_version != NORMALIZATION_VERSION
            )
            target_statement = select(tags.c.id, tags.c.name)
            if not full_rebuild:
                target_statement = target_statement.select_from(
                    tags.outerjoin(tag_search_cache, tags.c.id == tag_search_cache.c.tag_id)
                ).where(tag_search_cache.c.tag_id.is_(None))
            targets = [(int(row.id), str(row.name)) for row in connection.execute(target_statement)]

        prepared = self.prepare([name for _, name in targets])
        with self._database.begin() as connection:
            if full_rebuild and prepared.catalog_available:
                connection.execute(delete(tag_search_cache))
            self.store(connection, targets, prepared)
            if full_rebuild and prepared.catalog_available:
                statement = sqlite_insert(tag_search_cache_state).values(
                    id=1,
                    catalog_version=self._catalog.version,
                    normalization_version=NORMALIZATION_VERSION,
                )
                connection.execute(
                    statement.on_conflict_do_update(
                        index_elements=[tag_search_cache_state.c.id],
                        set_={
                            "catalog_version": statement.excluded.catalog_version,
                            "normalization_version": statement.excluded.normalization_version,
                        },
                    )
                )

    @staticmethod
    def store(
        connection: Connection,
        entries: Sequence[tuple[int, str]],
        prepared: PreparedTagSearch,
    ) -> None:
        unique_entries = dict(entries)
        if unique_entries:
            rows = [
                {
                    "tag_id": tag_id,
                    "name_nfkc": TagSearchIndex.normalize(name),
                    "cn_name_nfkc": prepared.aliases.get(name),
                }
                for tag_id, name in unique_entries.items()
            ]
            statement = sqlite_insert(tag_search_cache).values(rows)
            updated_values: dict[str, object] = {"name_nfkc": statement.excluded.name_nfkc}
            if prepared.catalog_available:
                updated_values["cn_name_nfkc"] = statement.excluded.cn_name_nfkc
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[tag_search_cache.c.tag_id],
                    set_=updated_values,
                )
            )
        if not prepared.catalog_available:
            connection.execute(delete(tag_search_cache_state))  # 清除状态以强制下次同步时重新构建缓存
