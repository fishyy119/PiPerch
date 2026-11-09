"""为本地图片媒体保存显示尺寸。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_0008"
down_revision: str | None = "20261108_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("media_files", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("media_files", sa.Column("height", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_files", "height")
    op.drop_column("media_files", "width")
