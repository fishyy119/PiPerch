"""保存 FANBOX 投稿下载所需的作者上下文，支持任务恢复与重试。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261107_0006"
down_revision: str | None = "20261107_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("download_items", sa.Column("author_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("download_items", "author_id")
