"""归档数据的类型转换、图片附件筛选与投稿映射。"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, cast
from urllib.parse import urlsplit

from piperch.domain.artworks import ArtworkType, RemoteArtwork
from piperch.domain.discovery import DiscoveryCandidate
from piperch.domain.sources import ArtworkSource
from piperch.errors import UpstreamError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif", ".tif", ".tiff"}


def as_mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, dict) else {}


def as_sequence(value: object) -> Sequence[object]:
    return cast("Sequence[object]", value) if isinstance(value, list) else ()


def as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def positive_id(value: object) -> int:
    text = str(value)
    return int(text) if text.isascii() and text.isdigit() and int(text) > 0 else 0


def image_attachments(post: Mapping[str, object]) -> list[Mapping[str, object]]:
    """仅接受正文附件中的图片，封面不能让纯文字或压缩包投稿进入图库。"""
    images: dict[str, Mapping[str, object]] = {}
    for value in as_sequence(post.get("attachments")):
        attachment = as_mapping(value)
        path = as_text(attachment.get("path"))
        suffix = PurePosixPath(path).suffix.lower()
        if path and (
            suffix in _IMAGE_EXTENSIONS
            or PurePosixPath(as_text(attachment.get("name"))).suffix.lower() in _IMAGE_EXTENSIONS
        ):
            images.setdefault(path, attachment)
    return list(images.values())


def file_path(file: Mapping[str, object]) -> str:
    path = as_text(file.get("path"))
    parsed = urlsplit(path)
    if (
        not path.startswith("/")
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or ".." in PurePosixPath(path).parts
    ):
        raise UpstreamError("invalid_fanbox_media", "FANBOX 图片路径无效。")
    return path


def original_url(file: Mapping[str, object]) -> str:
    node = positive_id(file.get("node"))
    # 未提供存储节点的附件使用站点统一的文件域名。
    host = f"https://n{node}.pawchive.pw" if node else "https://file.pawchive.pw"
    return f"{host}/data{file_path(file)}"


def thumbnail_url(file: Mapping[str, object]) -> str:
    return f"https://img.pawchive.pw/thumbnail/data{file_path(file)}"


def parse_total_pages(document: str, page_size: int) -> int | None:
    # 网站的总投稿数包含无图片投稿，不能根据过滤后的候选数重新计算页数。
    match = re.search(r"Showing\s+[\d,]+\s*-\s*[\d,]+\s+of\s+([\d,]+)", document)
    if match is None:
        return None
    total = int(match.group(1).replace(",", ""))
    return (total + page_size - 1) // page_size


def parse_candidate(post: Mapping[str, object], author_id: int, author_name: str) -> DiscoveryCandidate | None:
    images = image_attachments(post)
    if (
        not images
        or not positive_id(post.get("id"))
        or positive_id(post.get("user")) != author_id
        or post.get("service") != "fanbox"
    ):
        return None
    cover = as_mapping(post.get("file"))
    thumbnail = cover if PurePosixPath(as_text(cover.get("path"))).suffix.lower() in _IMAGE_EXTENSIONS else images[0]
    return DiscoveryCandidate(
        artwork_id=positive_id(post.get("id")),
        title=as_text(post.get("title")) or f"投稿 {post['id']}",
        author_name=author_name,
        artwork_type=ArtworkType.FANBOX,
        page_count=len(images),
        x_restrict=None,
        is_ai=None,
        thumbnail_url=thumbnail_url(thumbnail),
        author_id=author_id,
        preview_only=post.get("has_full") is False,
    )


def parse_artwork(
    post: Mapping[str, object], profile: Mapping[str, object], author_id: int, remote_id: int
) -> RemoteArtwork:
    if (
        post.get("service") != "fanbox"
        or positive_id(post.get("id")) != remote_id
        or positive_id(post.get("user")) != author_id
    ):
        raise UpstreamError("invalid_fanbox_response", "FANBOX 投稿信息与请求不一致。")
    images = image_attachments(post)
    if not images:
        raise UpstreamError("fanbox_no_images", "该 FANBOX 投稿没有可下载的图片附件。")
    return RemoteArtwork(
        remote_id=remote_id,
        source=ArtworkSource.FANBOX,
        artwork_type=ArtworkType.FANBOX,
        title=as_text(post.get("title")) or f"投稿 {remote_id}",
        description=as_text(post.get("content")),
        author_id=author_id,
        author_name=as_text(profile.get("name")) or str(author_id),
        author_account=None,
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=len(images),
        width=None,
        height=None,
        x_restrict=None,
        is_ai=None,
        published_at=as_text(post.get("published")) or None,
        original_urls=tuple(original_url(image) for image in images),
        thumbnail_url=thumbnail_url(images[0]),
    )
