"""移除作品尺寸和未使用的作者头像持久化字段。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261108_0007"
down_revision: str | None = "20261107_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 原生删列保留表和关联数据，以及已删除作品的自增序号上限。
    op.drop_column("authors", "avatar_url")
    op.drop_column("artworks", "width")
    op.drop_column("artworks", "height")


def downgrade() -> None:
    # 仅恢复字段结构，已删除的值需从升级前的数据库备份恢复。
    op.add_column("authors", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.add_column("artworks", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("artworks", sa.Column("height", sa.Integer(), nullable=True))
