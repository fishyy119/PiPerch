"""分离馆藏主键与平台原始 ID，保留已有 Pixiv 数据及关联。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261107_0005"
down_revision: str | None = "20261004_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("source", sa.String(16), nullable=True))
    op.add_column("artworks", sa.Column("remote_id", sa.BigInteger(), nullable=True))
    op.execute("UPDATE artworks SET source = 'pixiv', remote_id = id")
    # SQLite 无法直接变更主键类型和这些约束，按 Alembic 官方方式批量重建。
    with op.batch_alter_table("artworks", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.alter_column("id", existing_type=sa.BigInteger(), type_=sa.Integer(), autoincrement=True)
        batch.alter_column("source", existing_type=sa.String(16), nullable=False)
        batch.alter_column("remote_id", existing_type=sa.BigInteger(), nullable=False)
        batch.drop_constraint("ck_artworks_type", type_="check")
        batch.create_check_constraint(
            "ck_artworks_type",
            "(source = 'pixiv' AND artwork_type IN ('illust', 'manga', 'ugoira')) "
            "OR (source = 'fanbox' AND artwork_type = 'fanbox')",
        )
        batch.alter_column("x_restrict", existing_type=sa.Integer(), nullable=True, server_default=None)
        batch.alter_column("is_ai", existing_type=sa.Boolean(), nullable=True, server_default=None)
        batch.create_unique_constraint("uq_artworks_source_remote", ["source", "remote_id"])
        batch.create_check_constraint("ck_artworks_source", "source IN ('pixiv', 'fanbox')")
        batch.create_check_constraint("ck_artworks_remote_id", "remote_id > 0")
        batch.create_check_constraint(
            "ck_artworks_pixiv_metadata",
            "source != 'pixiv' OR (x_restrict IS NOT NULL AND is_ai IS NOT NULL)",
        )

    # 原生改名后再反射表，避免 batch 按旧列键解析新唯一约束。下载表只需重建一次。
    op.alter_column("download_items", "artwork_id", new_column_name="remote_id", existing_type=sa.BigInteger())
    op.add_column("download_items", sa.Column("source", sa.String(16), nullable=True))
    op.execute("UPDATE download_items SET source = 'pixiv'")
    with op.batch_alter_table("download_items") as batch:
        batch.drop_constraint("uq_download_items_job_artwork", type_="unique")
        batch.alter_column("source", existing_type=sa.String(16), nullable=False)
        batch.create_check_constraint("ck_download_items_source", "source IN ('pixiv', 'fanbox')")
        batch.create_check_constraint("ck_download_items_remote_id", "remote_id > 0")
        batch.create_unique_constraint("uq_download_items_job_source_remote", ["job_id", "source", "remote_id"])


def downgrade() -> None:
    op.alter_column("download_items", "remote_id", new_column_name="artwork_id", existing_type=sa.BigInteger())
    with op.batch_alter_table("download_items") as batch:
        batch.drop_constraint("uq_download_items_job_source_remote", type_="unique")
        batch.drop_constraint("ck_download_items_source", type_="check")
        batch.drop_constraint("ck_download_items_remote_id", type_="check")
        batch.drop_column("source")
        batch.create_unique_constraint("uq_download_items_job_artwork", ["job_id", "artwork_id"])
    with op.batch_alter_table("artworks", table_kwargs={"sqlite_autoincrement": False}) as batch:
        batch.drop_constraint("uq_artworks_source_remote", type_="unique")
        for name in ("ck_artworks_source", "ck_artworks_remote_id", "ck_artworks_pixiv_metadata", "ck_artworks_type"):
            batch.drop_constraint(name, type_="check")
        batch.drop_column("source")
        batch.drop_column("remote_id")
        batch.alter_column("id", existing_type=sa.Integer(), type_=sa.BigInteger(), autoincrement=False)
        batch.create_check_constraint("ck_artworks_type", "artwork_type IN ('illust', 'manga', 'ugoira')")
        batch.alter_column("x_restrict", existing_type=sa.Integer(), nullable=False, server_default="0")
        batch.alter_column("is_ai", existing_type=sa.Boolean(), nullable=False, server_default="0")
