from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from piperch.database import Database
    from piperch.paths import AppPaths
    from piperch.pixiv import PixivClient
    from piperch.repositories import ArtworkRepository, DownloadRepository
    from piperch.services.downloads import (
        DownloadEventBroker,
        DownloadSupervisor,
    )
    from piperch.services.library import LibraryService
    from piperch.services.thumbnails import ArtworkThumbnailCache
    from piperch.settings import SettingsManager


@dataclass(slots=True)
class AppContainer:
    paths: AppPaths
    database: Database
    settings: SettingsManager
    artworks: ArtworkRepository
    downloads: DownloadRepository
    pixiv: PixivClient
    supervisor: DownloadSupervisor
    events: DownloadEventBroker
    library: LibraryService
    thumbnails: ArtworkThumbnailCache
