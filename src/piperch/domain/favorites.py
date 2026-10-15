from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FavoriteState:
    artwork_id: int
    is_favorite: bool


@dataclass(frozen=True, slots=True)
class FavoriteSyncDiff:
    pixiv_favorite_count: int
    local_artwork_count: int
    local_favorite_count: int
    matched_favorite_count: int
    unavailable_locally_count: int
    add_artwork_ids: tuple[int, ...]
    remove_artwork_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class FavoriteSyncResult:
    added: int
    removed: int
