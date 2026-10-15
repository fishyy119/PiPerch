from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from piperch.domain.artworks import ArtworkType


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    artwork_id: int
    title: str
    author_name: str
    artwork_type: ArtworkType
    page_count: int
    x_restrict: int
    is_ai: bool
    thumbnail_url: str | None


@dataclass(frozen=True, slots=True)
class ArtworkDiscoveryFailure:
    artwork_id: int
    message: str


@dataclass(frozen=True, slots=True)
class ArtworkDiscoveryResult:
    candidates: list[DiscoveryCandidate]
    next_page: int | None
    failures: list[ArtworkDiscoveryFailure]


@dataclass(frozen=True, slots=True)
class RecommendedUser:
    user_id: int
    name: str
    comment: str
    avatar_url: str | None
    is_followed: bool
    artworks: tuple[DiscoveryCandidate, ...]


@dataclass(frozen=True, slots=True)
class FollowedUser:
    user_id: int
    name: str
    avatar_url: str | None


@dataclass(frozen=True, slots=True)
class UserProfile:
    avatar_url: str | None
    is_followed: bool | None
