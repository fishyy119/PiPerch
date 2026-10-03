"""移除下载项的页级进度字段。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261003_0002"
down_revision: str | None = "20260928_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("download_items") as batch_op:
        batch_op.drop_constraint("ck_download_items_progress_phase", type_="check")
        batch_op.drop_constraint("ck_download_items_progress_completed", type_="check")
        batch_op.drop_constraint("ck_download_items_progress_total", type_="check")
        batch_op.drop_column("progress_phase")
        batch_op.drop_column("progress_completed")
        batch_op.drop_column("progress_total")


def downgrade() -> None:
    with op.batch_alter_table("download_items") as batch_op:
        batch_op.add_column(sa.Column("progress_phase", sa.String(24), nullable=True))
        batch_op.add_column(
            sa.Column(
                "progress_completed",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("progress_total", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_download_items_progress_phase",
            "progress_phase IS NULL OR progress_phase IN ('preparing', 'downloading', 'finalizing')",
        )
        batch_op.create_check_constraint(
            "ck_download_items_progress_completed",
            "progress_completed >= 0",
        )
        batch_op.create_check_constraint(
            "ck_download_items_progress_total",
            "progress_total IS NULL OR progress_total >= 1",
        )
