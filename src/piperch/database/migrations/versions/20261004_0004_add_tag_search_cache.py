"""使用随附中文词典建立标签搜索缓存。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261004_0004"
down_revision: str | None = "20261004_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("tags", "translated_name")
    op.create_table(
        "tag_search_cache",
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("name_nfkc", sa.Text(), nullable=False),
        sa.Column("cn_name_nfkc", sa.Text(), nullable=True),
    )
    op.create_table(
        "tag_search_cache_state",
        sa.Column("id", sa.Integer(), autoincrement=False, primary_key=True),
        sa.Column("catalog_version", sa.Text(), nullable=False),
        sa.Column("normalization_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_tag_search_cache_state_singleton"),
    )


def downgrade() -> None:
    op.drop_table("tag_search_cache_state")
    op.drop_table("tag_search_cache")
    op.add_column("tags", sa.Column("translated_name", sa.Text(), nullable=True))
