from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from piperch.database import Database
    from piperch.paths import AppPaths
    from piperch.pixiv import PixivClient
    from piperch.repositories import ArtworkGroupRepository, ArtworkRepository, DownloadRepository, FavoriteRepository
    from piperch.services.downloads import (
        DownloadEventBroker,
        DownloadSupervisor,
    )
    from piperch.services.favorite_sync import FavoriteSyncService
    from piperch.services.library import LibraryService
    from piperch.services.storage import StorageMigrationService
    from piperch.services.thumbnails import ArtworkThumbnailCache
    from piperch.settings import SettingsManager


@dataclass(slots=True)
class AppContainer:
    paths: AppPaths
    database: Database
    settings: SettingsManager
    artworks: ArtworkRepository
    favorites: FavoriteRepository
    favorite_sync: FavoriteSyncService
    groups: ArtworkGroupRepository
    downloads: DownloadRepository
    pixiv: PixivClient
    supervisor: DownloadSupervisor
    events: DownloadEventBroker
    library: LibraryService
    thumbnails: ArtworkThumbnailCache
    storage: StorageMigrationService
    instance_id: str
