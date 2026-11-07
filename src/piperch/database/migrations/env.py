from __future__ import annotations

from contextlib import closing
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import engine_from_config, event, pool

from piperch.database.tables import metadata

if TYPE_CHECKING:
    import sqlite3

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def _set_foreign_keys(connection: sqlite3.Connection, *, enabled: bool) -> None:
    # 按 SQLAlchemy 的 SQLite 文档，在事务外设置 PRAGMA，随后恢复事务控制模式。
    previous_autocommit = connection.autocommit
    connection.autocommit = True
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}")
    finally:
        connection.autocommit = previous_autocommit


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Python 3.12+ 推荐的事务模式，确保 SQLite 的 DDL 也参与提交和回滚。
        connect_args={"autocommit": False},
    )

    @event.listens_for(connectable, "connect")
    def prepare_migration_connection(dbapi_connection: sqlite3.Connection, _connection_record: object) -> None:
        # Alembic batch 重建父表前必须关闭外键，以免 DROP TABLE 级联删除现有关联。
        _set_foreign_keys(dbapi_connection, enabled=False)

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                transactional_ddl=True,
            )
            try:
                # DDL、数据回填和版本号写入一起提交或回滚。
                with context.begin_transaction():
                    context.run_migrations()
            finally:
                _set_foreign_keys(connection.connection.driver_connection, enabled=True)
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
