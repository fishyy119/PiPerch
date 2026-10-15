from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BookmarkVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class BookmarkFolderKind(StrEnum):
    ALL = "all"
    UNCATEGORIZED = "uncategorized"
    TAG = "tag"


@dataclass(frozen=True, slots=True)
class RemoteBookmarkReference:
    bookmark_id: int
    private: bool


@dataclass(frozen=True, slots=True)
class PublicBookmark:
    artwork_id: int
    bookmark_id: int
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BookmarkFolderReference:
    visibility: BookmarkVisibility
    tag: str | None


@dataclass(frozen=True, slots=True)
class BookmarkFolder:
    reference: BookmarkFolderReference
    kind: BookmarkFolderKind
    name: str
    item_count: int
