from pathlib import Path

from sqlalchemy import inspect, text

from piperch.database import Database, run_migrations
from piperch.paths import AppPaths


def test_initial_migration_and_sqlite_pragmas(tmp_path: Path) -> None:
    paths = AppPaths.from_data_dir(tmp_path / "database")
    paths.ensure_directories()
    run_migrations(paths)
    run_migrations(paths)

    database = Database(paths.database)
    try:
        table_names = set(inspect(database.engine).get_table_names())
        with database.connect() as connection:
            foreign_keys = connection.scalar(text("PRAGMA foreign_keys"))
            journal_mode = connection.scalar(text("PRAGMA journal_mode"))
            synchronous = connection.scalar(text("PRAGMA synchronous"))
            busy_timeout = connection.scalar(text("PRAGMA busy_timeout"))
    finally:
        database.close()

    assert {
        "alembic_version",
        "artworks",
        "artwork_tags",
        "authors",
        "download_items",
        "download_jobs",
        "media_files",
        "series",
        "tags",
        "ugoira_frames",
    } <= table_names
    assert foreign_keys == 1
    assert str(journal_mode).lower() == "wal"
    assert synchronous == 1
    assert busy_timeout == 5000
