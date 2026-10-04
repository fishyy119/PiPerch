from __future__ import annotations

from typing import TYPE_CHECKING

from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from piperch.database import Database
    from piperch.domain import MediaRecord, RemoteArtwork
    from piperch.repositories import ArtworkGroupRepository, ArtworkRepository, FavoriteRepository
    from piperch.services.tag_search import TagSearchIndex


class ArtworkDownloadCommitService:
    """在单个事务中提交下载结果及其派生的本地状态。"""

    def __init__(
        self,
        database: Database,
        artworks: ArtworkRepository,
        favorites: FavoriteRepository,
        groups: ArtworkGroupRepository,
        tag_search: TagSearchIndex,
    ) -> None:
        self._database = database
        self._artworks = artworks
        self._favorites = favorites
        self._groups = groups
        self._tag_search = tag_search

    def commit(
        self,
        artwork: RemoteArtwork,
        media: Sequence[MediaRecord],
        bookmark_tags: Sequence[str] | None = None,
    ) -> None:
        now = utc_now_text()
        prepared_tag_search = self._tag_search.prepare([tag.name for tag in artwork.tags])

        with self._database.begin() as connection:
            self._artworks.upsert_author(connection, artwork, now)
            self._artworks.upsert_series(connection, artwork, now)
            is_new_artwork = self._artworks.upsert_artwork(connection, artwork, now)
            indexed_tags = self._artworks.replace_tags(connection, artwork.artwork_id, artwork.tags)
            self._tag_search.store(connection, indexed_tags, prepared_tag_search)
            self._artworks.replace_media(connection, artwork.artwork_id, media, now)
            self._artworks.replace_ugoira_frames(connection, artwork.artwork_id, artwork.ugoira_frames)

            if is_new_artwork and artwork.bookmark_data is not None:
                self._favorites.ensure_favorite(connection, artwork.artwork_id, now)
            if is_new_artwork and bookmark_tags is not None:
                self._groups.import_bookmark_groups(
                    connection,
                    artwork.artwork_id,
                    bookmark_tags,
                    now,
                )
