"""增加本地收藏与收藏分组。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261003_0003"
down_revision: str | None = "20261001_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorite_artworks",
        sa.Column(
            "artwork_id",
            sa.BigInteger(),
            sa.ForeignKey("artworks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "favorite_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("name", name="uq_favorite_groups_name"),
    )
    op.create_table(
        "favorite_group_items",
        sa.Column(
            "artwork_id",
            sa.BigInteger(),
            sa.ForeignKey("favorite_artworks.artwork_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("favorite_groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_favorite_group_items_group_artwork",
        "favorite_group_items",
        ["group_id", "artwork_id"],
    )


def downgrade() -> None:
    op.drop_table("favorite_group_items")
    op.drop_table("favorite_groups")
    op.drop_table("favorite_artworks")
