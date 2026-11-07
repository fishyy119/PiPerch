from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from importlib.resources import as_file, files
from typing import TYPE_CHECKING, Protocol, cast
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Connection

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from piperch.paths import AppPaths


def sqlite_url(path: Path) -> URL:
    return URL.create("sqlite+pysqlite", database=str(path))


def run_migrations(paths: AppPaths) -> None:
    migration_scripts = files("piperch.database").joinpath("migrations")
    with as_file(migration_scripts) as migration_path:
        config = Config()
        config.set_main_option("script_location", str(migration_path))
        migration_url = sqlite_url(paths.database).render_as_string(False).replace("%", "%%")
        config.set_main_option("sqlalchemy.url", migration_url)
        if paths.database.is_file():
            with closing(sqlite3.connect(paths.database)) as source:
                has_version = source.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                ).fetchone()
                current = source.execute("SELECT version_num FROM alembic_version").fetchone() if has_version else None
                head = ScriptDirectory.from_config(config).get_current_head()
                if current is not None and current[0] != head:
                    # SQLite backup 会一并读取 WAL 中已提交的数据，不能只复制主数据库文件。
                    backup = paths.database.with_name(f"{paths.database.stem}.before-{current[0]}-{uuid4().hex}.sqlite")
                    with closing(sqlite3.connect(backup)) as target:
                        source.backup(target)
        command.upgrade(config, "head")


class Database:
    def __init__(self, path: Path) -> None:
        self.engine = create_engine(sqlite_url(path))
        event.listen(self.engine, "connect", self._configure_sqlite)

    @staticmethod
    def _configure_sqlite(dbapi_connection: object, _connection_record: object) -> None:
        cursor = cast("_DbapiConnection", dbapi_connection).cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

    @contextmanager
    def connect(self) -> Generator[Connection]:
        with self.engine.connect() as connection:
            yield connection

    @contextmanager
    def begin(self) -> Generator[Connection]:
        with self.engine.begin() as connection:
            yield connection

    def close(self) -> None:
        self.engine.dispose()


class _DbapiCursor(Protocol):
    def execute(self, statement: str) -> object: ...

    def close(self) -> None: ...


class _DbapiConnection(Protocol):
    def cursor(self) -> _DbapiCursor: ...
