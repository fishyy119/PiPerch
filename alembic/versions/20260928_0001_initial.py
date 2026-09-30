"""建立首版数据库结构。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authors",
        sa.Column("id", sa.BigInteger(), autoincrement=False, primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("account", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "series",
        sa.Column("id", sa.BigInteger(), autoincrement=False, primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "author_id",
            sa.BigInteger(),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "artworks",
        sa.Column("id", sa.BigInteger(), autoincrement=False, primary_key=True),
        sa.Column("artwork_type", sa.String(16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "author_id",
            sa.BigInteger(),
            sa.ForeignKey("authors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "series_id",
            sa.BigInteger(),
            sa.ForeignKey("series.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("x_restrict", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_ai", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("published_at", sa.String(40), nullable=True),
        sa.Column("downloaded_at", sa.String(40), nullable=False),
        sa.Column("metadata_updated_at", sa.String(40), nullable=False),
        sa.CheckConstraint(
            "artwork_type IN ('illust', 'manga', 'ugoira')",
            name="ck_artworks_type",
        ),
        sa.CheckConstraint("page_count >= 1", name="ck_artworks_page_count"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("translated_name", sa.Text(), nullable=True),
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )
    op.create_table(
        "artwork_tags",
        sa.Column(
            "artwork_id",
            sa.BigInteger(),
            sa.ForeignKey("artworks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "artwork_id",
            sa.BigInteger(),
            sa.ForeignKey("artworks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=True),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("downloaded_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("relative_path", name="uq_media_files_relative_path"),
        sa.UniqueConstraint(
            "artwork_id",
            "role",
            "page_index",
            name="uq_media_artwork_role_page",
        ),
        sa.CheckConstraint("byte_size > 0", name="ck_media_files_size"),
    )
    op.create_table(
        "ugoira_frames",
        sa.Column(
            "artwork_id",
            sa.BigInteger(),
            sa.ForeignKey("artworks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("delay_ms", sa.Integer(), nullable=False),
        sa.CheckConstraint("sequence >= 0", name="ck_ugoira_frames_sequence"),
        sa.CheckConstraint("delay_ms >= 0", name="ck_ugoira_frames_delay"),
    )
    op.create_table(
        "download_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_label", sa.Text(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("started_at", sa.String(40), nullable=True),
        sa.Column("finished_at", sa.String(40), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'succeeded', 'partiallySucceeded', 'failed', 'cancelled')",
            name="ck_download_jobs_state",
        ),
    )
    op.create_table(
        "download_items",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("download_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artwork_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.String(40), nullable=True),
        sa.Column("finished_at", sa.String(40), nullable=True),
        sa.UniqueConstraint("job_id", "artwork_id", name="uq_download_items_job_artwork"),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'skipped', 'succeeded', 'failed', 'cancelled')",
            name="ck_download_items_state",
        ),
    )

    op.create_index("ix_artworks_downloaded_at", "artworks", ["downloaded_at"])
    op.create_index("ix_artworks_published_at", "artworks", ["published_at"])
    op.create_index("ix_artworks_author", "artworks", ["author_id"])
    op.create_index("ix_artworks_series", "artworks", ["series_id"])
    op.create_index("ix_artworks_type", "artworks", ["artwork_type"])
    op.create_index("ix_artworks_restrict", "artworks", ["x_restrict"])
    op.create_index("ix_artworks_ai", "artworks", ["is_ai"])
    op.create_index(
        "ix_artwork_tags_tag_artwork",
        "artwork_tags",
        ["tag_id", "artwork_id"],
    )
    op.create_index(
        "ix_download_jobs_state_created",
        "download_jobs",
        ["state", "created_at"],
    )
    op.create_index(
        "ix_download_items_job_state",
        "download_items",
        ["job_id", "state"],
    )


def downgrade() -> None:
    op.drop_table("download_items")
    op.drop_table("download_jobs")
    op.drop_table("ugoira_frames")
    op.drop_table("media_files")
    op.drop_table("artwork_tags")
    op.drop_table("tags")
    op.drop_table("artworks")
    op.drop_table("series")
    op.drop_table("authors")
