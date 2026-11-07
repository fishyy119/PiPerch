from __future__ import annotations

from typing import TYPE_CHECKING

from piperch.domain.sources import ArtworkSource
from piperch.errors import AppError
from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from piperch.database import Database
    from piperch.domain.artworks import MediaRecord, RemoteArtwork
    from piperch.repositories import ArtworkGroupRepository, ArtworkRepository, FavoriteRepository
    from piperch.services.library_commits import LibraryCommitCoordinator
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
        *,
        library_commits: LibraryCommitCoordinator,
    ) -> None:
        self._database = database
        self._artworks = artworks
        self._favorites = favorites
        self._groups = groups
        self._tag_search = tag_search
        self._library_commits = library_commits

    def commit(
        self,
        artwork: RemoteArtwork,
        media: Sequence[MediaRecord],
        bookmark_tags: Sequence[str] | None = None,
    ) -> int:
        return self._library_commits.commit_addition(
            lambda: self._commit(artwork, media, bookmark_tags),
            source=artwork.source,
            remote_id=artwork.remote_id,
        )

    def _commit(
        self,
        artwork: RemoteArtwork,
        media: Sequence[MediaRecord],
        bookmark_tags: Sequence[str] | None,
    ) -> int:
        now = utc_now_text()
        if artwork.source is ArtworkSource.FANBOX:
            pages = [item for item in media if item.role == "page"]
            if (
                not pages
                or len(pages) != artwork.page_count
                or any(not item.mime_type.startswith("image/") for item in pages)
            ):
                raise AppError("fanbox_images_required", "FANBOX 投稿必须包含已保存的图片附件。", 400)
        prepared_tag_search = self._tag_search.prepare(artwork.tags)

        with self._database.begin() as connection:
            self._artworks.upsert_author(connection, artwork, now)
            self._artworks.upsert_series(connection, artwork, now)
            artwork_id, is_new_artwork = self._artworks.upsert_artwork(connection, artwork, now)
            indexed_tags = self._artworks.replace_tags(connection, artwork_id, artwork.tags)
            self._tag_search.store(connection, indexed_tags, prepared_tag_search)
            self._artworks.replace_media(connection, artwork_id, media, now)
            self._artworks.replace_ugoira_frames(connection, artwork_id, artwork.ugoira_frames)

            if is_new_artwork and artwork.bookmark_data is not None:
                self._favorites.ensure_favorite(connection, artwork_id, now)
            if is_new_artwork and bookmark_tags is not None:
                self._groups.import_bookmark_groups(
                    connection,
                    artwork_id,
                    bookmark_tags,
                    now,
                )
        return artwork_id
