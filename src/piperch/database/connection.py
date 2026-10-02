from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import as_file, files
from typing import TYPE_CHECKING, Protocol, cast

from alembic import command
from alembic.config import Config
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
