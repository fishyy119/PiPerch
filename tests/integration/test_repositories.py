from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from piperch.database import Database, run_migrations
from piperch.domain import ArtworkType, ItemState, MediaRecord, RemoteArtwork, TagRecord
from piperch.paths import AppPaths
from piperch.repositories import ArtworkRepository, DownloadRepository
from piperch.services.library import LibraryService
from piperch.settings import SettingsManager

if TYPE_CHECKING:
    from pathlib import Path


def _artwork(artwork_id: int, tags: tuple[TagRecord, ...]) -> RemoteArtwork:
    return RemoteArtwork(
        artwork_id=artwork_id,
        artwork_type=ArtworkType.ILLUST,
        title=f"测试作品 {artwork_id}",
        description="简介",
        author_id=100,
        author_name="测试作者",
        author_account="tester",
        author_avatar_url=None,
        series_id=None,
        series_title=None,
        page_count=1,
        width=1000,
        height=1200,
        x_restrict=0,
        is_ai=False,
        published_at="2026-09-28T00:00:00Z",
        original_urls=("https://i.pximg.net/img-original/example.jpg",),
        thumbnail_url=None,
        tags=tags,
    )


def _repositories(
    tmp_path: Path,
) -> tuple[AppPaths, Database, SettingsManager, ArtworkRepository, DownloadRepository]:
    paths = AppPaths.from_data_dir(tmp_path / "repository")
    paths.ensure_directories()
    run_migrations(paths)
    database = Database(paths.database)
    settings = SettingsManager(paths.settings, paths.default_library, database)
    settings.initialize()
    return paths, database, settings, ArtworkRepository(database), DownloadRepository(database)


def test_gallery_tag_filter_uses_and_semantics(tmp_path: Path) -> None:
    _, database, _, artworks, _ = _repositories(tmp_path)
    try:
        artworks.save_download(
            _artwork(1, (TagRecord("风景"), TagRecord("蓝天"))),
            [MediaRecord("page", "100/1/1_p0.jpg", "image/jpeg", 10, 0)],
        )
        artworks.save_download(
            _artwork(2, (TagRecord("风景"),)),
            [MediaRecord("page", "100/2/2_p0.jpg", "image/jpeg", 10, 0)],
        )
        available_tags = artworks.list_tags("", 50)
        tag_ids = [tag_id for tag_id, _, _ in available_tags]

        items, total = artworks.list_artworks(
            page=0,
            size=24,
            search="",
            tag_ids=tag_ids,
            author_id=None,
            series_id=None,
            artwork_type=None,
            rating="all",
            ai="all",
            sort="id",
            order="asc",
        )
    finally:
        database.close()

    assert total == 1
    assert [item.artwork_id for item in items] == [1]


def test_related_artworks_combine_author_and_shared_tags(tmp_path: Path) -> None:
    _, database, _, artworks, _ = _repositories(tmp_path)
    target = _artwork(1, (TagRecord("风景"), TagRecord("蓝天")))
    candidates = (
        _artwork(2, (TagRecord("人物"),)),
        replace(
            _artwork(3, target.tags),
            author_id=200,
            author_name="其他作者",
        ),
        replace(
            _artwork(4, (TagRecord("风景"),)),
            author_id=201,
            author_name="第三作者",
        ),
        replace(
            _artwork(5, (TagRecord("无关"),)),
            author_id=202,
            author_name="无关作者",
        ),
    )
    try:
        for artwork in (target, *candidates):
            artworks.save_download(
                artwork,
                [
                    MediaRecord(
                        "page",
                        f"{artwork.author_id}/{artwork.artwork_id}/{artwork.artwork_id}_p0.jpg",
                        "image/jpeg",
                        10,
                        0,
                    )
                ],
            )
        related = artworks.list_related_artworks(1, 10)
    finally:
        database.close()

    assert [item.artwork_id for item in related] == [2, 3, 4]


def test_find_existing_artwork_ids_ignores_unknown_and_duplicate_ids(tmp_path: Path) -> None:
    _, database, _, artworks, _ = _repositories(tmp_path)
    try:
        artworks.save_download(
            _artwork(101, ()),
            [MediaRecord("page", "100/101/101_p0.jpg", "image/jpeg", 10, 0)],
        )
        existing_ids = artworks.find_existing_ids([101, 101, 202])
    finally:
        database.close()

    assert existing_ids == {101}


def test_download_completeness_requires_every_page(tmp_path: Path) -> None:
    _, database, settings, artworks, _ = _repositories(tmp_path)
    artwork = replace(
        _artwork(101, ()),
        page_count=2,
        original_urls=("https://i.pximg.net/101_p0.jpg", "https://i.pximg.net/101_p1.jpg"),
    )
    library_root = settings.get().library_root
    first_path = library_root / "100/101/101_p0.jpg"
    second_path = library_root / "100/101/101_p1.jpg"
    first_path.parent.mkdir(parents=True)
    first_path.write_bytes(b"first")
    try:
        first_page = MediaRecord("page", "100/101/101_p0.jpg", "image/jpeg", 5, 0)
        artworks.save_download(artwork, [first_page])
        incomplete = artworks.is_complete(101, library_root)

        second_path.write_bytes(b"second")
        second_page = MediaRecord("page", "100/101/101_p1.jpg", "image/jpeg", 6, 1)
        artworks.save_download(artwork, [first_page, second_page])
        complete = artworks.is_complete(101, library_root)
    finally:
        database.close()

    assert incomplete is False
    assert complete is True


def test_delete_metadata_removes_unused_gallery_facets(tmp_path: Path) -> None:
    _, database, _, artworks, _ = _repositories(tmp_path)
    artwork = replace(
        _artwork(101, (TagRecord("风景"),)),
        series_id=200,
        series_title="测试系列",
    )
    try:
        artworks.save_download(
            artwork,
            [MediaRecord("page", "100/101/101_p0.jpg", "image/jpeg", 10, 0)],
        )
        deleted = artworks.delete_metadata([101])
        available_tags = artworks.list_tags("", 50)
        available_authors, author_total = artworks.list_authors(0, 50, "")
        available_series, series_total = artworks.list_series(0, 50, "")
    finally:
        database.close()

    assert deleted == 1
    assert available_tags == []
    assert available_authors == []
    assert author_total == 0
    assert available_series == []
    assert series_total == 0


def test_download_job_transitions_and_retry(tmp_path: Path) -> None:
    _, database, _, _, downloads = _repositories(tmp_path)
    try:
        job_id = downloads.create_job([1, 1, 2], "测试任务")
        first = downloads.claim_next()
        assert first is not None
        _, first_item = first
        downloads.complete_item(first_item.item_id, ItemState.SUCCEEDED)

        second = downloads.claim_next()
        assert second is not None
        _, second_item = second
        downloads.complete_item(second_item.item_id, ItemState.FAILED, "模拟失败")

        failed_job = downloads.get_job(job_id)
        assert failed_job.state.value == "partiallySucceeded"
        assert failed_job.error_summary == "模拟失败"
        downloads.retry(job_id)
        retried_job = downloads.get_job(job_id)
    finally:
        database.close()

    assert retried_job.state.value == "queued"
    assert retried_job.counts[ItemState.QUEUED] == 1


def test_interrupted_delete_is_restored_when_metadata_still_exists(tmp_path: Path) -> None:
    paths, database, settings, artworks, _ = _repositories(tmp_path)
    source = settings.get().library_root / "100" / "1"
    pending = paths.staging / "delete" / "100" / "1-interrupted"
    try:
        artworks.save_download(
            _artwork(1, (TagRecord("风景"),)),
            [MediaRecord("page", "100/1/1_p0.jpg", "image/jpeg", 4, 0)],
        )
        source.mkdir(parents=True)
        (source / "1_p0.jpg").write_bytes(b"test")
        pending.parent.mkdir(parents=True)
        source.replace(pending)

        LibraryService(paths, settings, artworks).recover_pending_deletes()
    finally:
        database.close()

    assert (source / "1_p0.jpg").read_bytes() == b"test"
    assert not pending.exists()


def test_running_download_is_requeued_during_recovery(tmp_path: Path) -> None:
    _, database, _, _, downloads = _repositories(tmp_path)
    try:
        job_id = downloads.create_job([123], "中断任务")
        assert downloads.claim_next() is not None

        downloads.recover_interrupted()
        recovered = downloads.get_job(job_id)
    finally:
        database.close()

    assert recovered.state.value == "queued"
    assert recovered.items[0].state is ItemState.QUEUED
