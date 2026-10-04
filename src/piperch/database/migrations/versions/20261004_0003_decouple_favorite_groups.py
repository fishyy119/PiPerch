"""将分组设为独立的本地作品组织方式。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261004_0003"
down_revision: str | None = "20261003_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("favorite_groups", "artwork_groups")
    op.create_table(
        "artwork_group_items",
        sa.Column(
            "artwork_id",
            sa.BigInteger(),
            sa.ForeignKey("artworks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("artwork_groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.execute(
        "INSERT INTO artwork_group_items (artwork_id, group_id) SELECT artwork_id, group_id FROM favorite_group_items"
    )
    op.drop_table("favorite_group_items")
    op.create_index(
        "ix_artwork_group_items_group_artwork",
        "artwork_group_items",
        ["group_id", "artwork_id"],
    )


def downgrade() -> None:
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
            sa.ForeignKey("artwork_groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.execute(
        "INSERT INTO favorite_group_items (artwork_id, group_id) "
        "SELECT items.artwork_id, items.group_id FROM artwork_group_items AS items "
        "JOIN favorite_artworks AS favorites ON favorites.artwork_id = items.artwork_id"
    )
    op.drop_table("artwork_group_items")
    op.rename_table("artwork_groups", "favorite_groups")
    op.create_index(
        "ix_favorite_group_items_group_artwork",
        "favorite_group_items",
        ["group_id", "artwork_id"],
    )
