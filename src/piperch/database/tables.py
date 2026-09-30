from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

authors = Table(
    "authors",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=False),
    Column("name", Text, nullable=False),
    Column("account", Text, nullable=True),
    Column("avatar_url", Text, nullable=True),
    Column("updated_at", String(40), nullable=False),
)

series = Table(
    "series",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=False),
    Column("title", Text, nullable=False),
    Column("author_id", BigInteger, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
    Column("updated_at", String(40), nullable=False),
)

artworks = Table(
    "artworks",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=False),
    Column("artwork_type", String(16), nullable=False),
    Column("title", Text, nullable=False),
    Column("description", Text, nullable=False, server_default=""),
    Column("author_id", BigInteger, ForeignKey("authors.id", ondelete="RESTRICT"), nullable=False),
    Column("series_id", BigInteger, ForeignKey("series.id", ondelete="SET NULL"), nullable=True),
    Column("page_count", Integer, nullable=False),
    Column("width", Integer, nullable=True),
    Column("height", Integer, nullable=True),
    Column("x_restrict", Integer, nullable=False, server_default="0"),
    Column("is_ai", Boolean, nullable=False, server_default="0"),
    Column("published_at", String(40), nullable=True),
    Column("downloaded_at", String(40), nullable=False),
    Column("metadata_updated_at", String(40), nullable=False),
    CheckConstraint(
        "artwork_type IN ('illust', 'manga', 'ugoira')",
        name="ck_artworks_type",
    ),
    CheckConstraint("page_count >= 1", name="ck_artworks_page_count"),
)

tags = Table(
    "tags",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False, unique=True),
    Column("translated_name", Text, nullable=True),
)

artwork_tags = Table(
    "artwork_tags",
    metadata,
    Column(
        "artwork_id",
        BigInteger,
        ForeignKey("artworks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

media_files = Table(
    "media_files",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "artwork_id",
        BigInteger,
        ForeignKey("artworks.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String(24), nullable=False),
    Column("page_index", Integer, nullable=True),
    Column("relative_path", Text, nullable=False, unique=True),
    Column("mime_type", String(100), nullable=False),
    Column("byte_size", BigInteger, nullable=False),
    Column("downloaded_at", String(40), nullable=False),
    UniqueConstraint("artwork_id", "role", "page_index", name="uq_media_artwork_role_page"),
    CheckConstraint("byte_size > 0", name="ck_media_files_size"),
)

ugoira_frames = Table(
    "ugoira_frames",
    metadata,
    Column(
        "artwork_id",
        BigInteger,
        ForeignKey("artworks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("sequence", Integer, primary_key=True),
    Column("file_name", Text, nullable=False),
    Column("delay_ms", Integer, nullable=False),
    CheckConstraint("sequence >= 0", name="ck_ugoira_frames_sequence"),
    CheckConstraint("delay_ms >= 0", name="ck_ugoira_frames_delay"),
)

download_jobs = Table(
    "download_jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("source_label", Text, nullable=False),
    Column("state", String(32), nullable=False),
    Column("cancel_requested", Boolean, nullable=False, server_default="0"),
    Column("created_at", String(40), nullable=False),
    Column("started_at", String(40), nullable=True),
    Column("finished_at", String(40), nullable=True),
    Column("error_summary", Text, nullable=True),
    CheckConstraint(
        "state IN ('queued', 'running', 'succeeded', 'partiallySucceeded', 'failed', 'cancelled')",
        name="ck_download_jobs_state",
    ),
)

download_items = Table(
    "download_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "job_id",
        String(36),
        ForeignKey("download_jobs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("artwork_id", BigInteger, nullable=False),
    Column("state", String(16), nullable=False),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("error", Text, nullable=True),
    Column("started_at", String(40), nullable=True),
    Column("finished_at", String(40), nullable=True),
    UniqueConstraint("job_id", "artwork_id", name="uq_download_items_job_artwork"),
    CheckConstraint(
        "state IN ('queued', 'running', 'skipped', 'succeeded', 'failed', 'cancelled')",
        name="ck_download_items_state",
    ),
)

Index("ix_artworks_downloaded_at", artworks.c.downloaded_at)
Index("ix_artworks_published_at", artworks.c.published_at)
Index("ix_artworks_author", artworks.c.author_id)
Index("ix_artworks_series", artworks.c.series_id)
Index("ix_artworks_type", artworks.c.artwork_type)
Index("ix_artworks_restrict", artworks.c.x_restrict)
Index("ix_artworks_ai", artworks.c.is_ai)
Index("ix_artwork_tags_tag_artwork", artwork_tags.c.tag_id, artwork_tags.c.artwork_id)
Index("ix_download_jobs_state_created", download_jobs.c.state, download_jobs.c.created_at)
Index("ix_download_items_job_state", download_items.c.job_id, download_items.c.state)
