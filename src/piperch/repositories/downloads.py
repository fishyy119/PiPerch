# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# SQLAlchemy Core 的泛型表达式会丢失部分列类型，此文件在数据库边界精确关闭相关噪音。
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from sqlalchemy import and_, func, insert, select, update

from piperch.database.tables import download_items, download_jobs
from piperch.domain import (
    DownloadItemRecord,
    DownloadJobRecord,
    DownloadProgress,
    DownloadProgressPhase,
    ItemState,
    JobState,
)
from piperch.errors import ConflictError, NotFoundError
from piperch.repositories._rows import integer, optional_integer, optional_string, string
from piperch.utils.datetime import utc_now_text

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.engine import RowMapping

    from piperch.database import Database


class DownloadRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create_job(self, artwork_ids: Iterable[int], source_label: str) -> str:
        unique_ids = tuple(dict.fromkeys(artwork_ids))
        job_id = str(uuid4())
        now = utc_now_text()
        with self._database.begin() as connection:
            connection.execute(
                insert(download_jobs).values(
                    id=job_id,
                    source_label=source_label,
                    state=JobState.QUEUED.value,
                    cancel_requested=False,
                    created_at=now,
                )
            )
            connection.execute(
                insert(download_items),
                [
                    {
                        "job_id": job_id,
                        "artwork_id": artwork_id,
                        "state": ItemState.QUEUED.value,
                        "attempts": 0,
                    }
                    for artwork_id in unique_ids
                ],
            )
        return job_id

    def recover_interrupted(self) -> None:
        with self._database.begin() as connection:
            connection.execute(
                update(download_items)
                .where(download_items.c.state == ItemState.RUNNING.value)
                .values(
                    state=ItemState.QUEUED.value,
                    started_at=None,
                    progress_phase=None,
                    progress_completed=0,
                    progress_total=None,
                )
            )
            connection.execute(
                update(download_jobs)
                .where(download_jobs.c.state == JobState.RUNNING.value)
                .values(state=JobState.QUEUED.value, started_at=None)
            )

    def claim_next(self) -> tuple[str, DownloadItemRecord] | None:
        with self._database.begin() as connection:
            job_row = (
                connection.execute(
                    select(download_jobs)
                    .where(download_jobs.c.state.in_([JobState.QUEUED.value, JobState.RUNNING.value]))
                    .order_by(download_jobs.c.created_at.asc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if job_row is None:
                return None
            job_id = string(job_row["id"])
            if bool(job_row["cancel_requested"]):
                connection.execute(
                    update(download_items)
                    .where(
                        and_(
                            download_items.c.job_id == job_id,
                            download_items.c.state == ItemState.QUEUED.value,
                        )
                    )
                    .values(state=ItemState.CANCELLED.value, finished_at=utc_now_text())
                )
                self._finalize(connection, job_id)
                return None
            item_row = (
                connection.execute(
                    select(download_items)
                    .where(
                        and_(
                            download_items.c.job_id == job_id,
                            download_items.c.state == ItemState.QUEUED.value,
                        )
                    )
                    .order_by(download_items.c.id.asc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if item_row is None:
                self._finalize(connection, job_id)
                return None
            now = utc_now_text()
            connection.execute(
                update(download_jobs)
                .where(download_jobs.c.id == job_id)
                .values(state=JobState.RUNNING.value, started_at=job_row["started_at"] or now)
            )
            item_id = integer(item_row["id"])
            attempts = integer(item_row["attempts"]) + 1
            connection.execute(
                update(download_items)
                .where(download_items.c.id == item_id)
                .values(
                    state=ItemState.RUNNING.value,
                    attempts=attempts,
                    error=None,
                    started_at=now,
                    finished_at=None,
                    progress_phase=DownloadProgressPhase.PREPARING.value,
                    progress_completed=0,
                    progress_total=None,
                )
            )
            return (
                job_id,
                DownloadItemRecord(
                    item_id=item_id,
                    artwork_id=integer(item_row["artwork_id"]),
                    state=ItemState.RUNNING,
                    attempts=attempts,
                    error=None,
                ),
            )

    def update_item_progress(
        self,
        item_id: int,
        phase: DownloadProgressPhase,
        completed_pages: int,
        total_pages: int | None,
    ) -> None:
        if completed_pages < 0:
            raise ValueError("已完成页数不能为负数。")
        if total_pages is not None and (total_pages < 1 or completed_pages > total_pages):
            raise ValueError("下载页数进度无效。")
        with self._database.begin() as connection:
            connection.execute(
                update(download_items)
                .where(
                    and_(
                        download_items.c.id == item_id,
                        download_items.c.state == ItemState.RUNNING.value,
                    )
                )
                .values(
                    progress_phase=phase.value,
                    progress_completed=completed_pages,
                    progress_total=total_pages,
                )
            )

    def complete_item(self, item_id: int, state: ItemState, error: str | None = None) -> None:
        with self._database.begin() as connection:
            job_id = connection.scalar(select(download_items.c.job_id).where(download_items.c.id == item_id))
            if job_id is None:
                return
            connection.execute(
                update(download_items)
                .where(download_items.c.id == item_id)
                .values(
                    state=state.value,
                    error=error,
                    finished_at=utc_now_text(),
                    progress_phase=None,
                    progress_completed=0,
                    progress_total=None,
                )
            )
            remaining = connection.scalar(
                select(func.count())
                .select_from(download_items)
                .where(
                    and_(
                        download_items.c.job_id == job_id,
                        download_items.c.state.in_([ItemState.QUEUED.value, ItemState.RUNNING.value]),
                    )
                )
            )
            if not remaining:
                self._finalize(connection, cast("str", job_id))

    def request_cancel(self, job_id: str) -> None:
        with self._database.begin() as connection:
            result = connection.execute(
                update(download_jobs)
                .where(
                    and_(
                        download_jobs.c.id == job_id,
                        download_jobs.c.state.in_([JobState.QUEUED.value, JobState.RUNNING.value]),
                    )
                )
                .values(cancel_requested=True)
            )
            if not result.rowcount:
                raise NotFoundError("未找到可取消的下载任务。")
            connection.execute(
                update(download_items)
                .where(
                    and_(
                        download_items.c.job_id == job_id,
                        download_items.c.state == ItemState.QUEUED.value,
                    )
                )
                .values(
                    state=ItemState.CANCELLED.value,
                    finished_at=utc_now_text(),
                    progress_phase=None,
                    progress_completed=0,
                    progress_total=None,
                )
            )

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._database.connect() as connection:
            value = connection.scalar(select(download_jobs.c.cancel_requested).where(download_jobs.c.id == job_id))
        return bool(value)

    def retry(self, job_id: str) -> None:
        with self._database.begin() as connection:
            failed_count = connection.scalar(
                select(func.count())
                .select_from(download_items)
                .where(
                    and_(
                        download_items.c.job_id == job_id,
                        download_items.c.state == ItemState.FAILED.value,
                    )
                )
            )
            if not failed_count:
                raise ConflictError("nothing_to_retry", "该任务没有可重试的失败项。")
            connection.execute(
                update(download_items)
                .where(
                    and_(
                        download_items.c.job_id == job_id,
                        download_items.c.state == ItemState.FAILED.value,
                    )
                )
                .values(
                    state=ItemState.QUEUED.value,
                    error=None,
                    finished_at=None,
                    progress_phase=None,
                    progress_completed=0,
                    progress_total=None,
                )
            )
            connection.execute(
                update(download_jobs)
                .where(download_jobs.c.id == job_id)
                .values(
                    state=JobState.QUEUED.value,
                    cancel_requested=False,
                    finished_at=None,
                    error_summary=None,
                )
            )

    def list_jobs(self, page: int, size: int, include_items: bool = False) -> tuple[list[DownloadJobRecord], int]:
        with self._database.connect() as connection:
            total = int(connection.scalar(select(func.count()).select_from(download_jobs)) or 0)
            rows = connection.execute(
                select(download_jobs).order_by(download_jobs.c.created_at.desc()).offset(page * size).limit(size)
            ).mappings()
            jobs = [self._job_from_row(connection, row, include_items) for row in rows]
        return jobs, total

    def get_job(self, job_id: str) -> DownloadJobRecord:
        with self._database.connect() as connection:
            row = connection.execute(select(download_jobs).where(download_jobs.c.id == job_id)).mappings().first()
            if row is None:
                raise NotFoundError("未找到下载任务。")
            return self._job_from_row(connection, row, True)

    @staticmethod
    def _finalize(connection: object, job_id: str) -> None:
        rows = connection.execute(
            select(download_items.c.state, func.count().label("item_count"))
            .where(download_items.c.job_id == job_id)
            .group_by(download_items.c.state)
        ).all()
        counts = Counter({string(row.state): integer(row.item_count) for row in rows})
        total = sum(counts.values())
        if counts[ItemState.CANCELLED.value] == total:
            state = JobState.CANCELLED
        elif counts[ItemState.FAILED.value] == total:
            state = JobState.FAILED
        elif counts[ItemState.FAILED.value] or counts[ItemState.CANCELLED.value]:
            state = JobState.PARTIALLY_SUCCEEDED
        else:
            state = JobState.SUCCEEDED
        failed_count = counts[ItemState.FAILED.value]
        first_error = optional_string(
            connection.scalar(
                select(download_items.c.error)
                .where(
                    and_(
                        download_items.c.job_id == job_id,
                        download_items.c.state == ItemState.FAILED.value,
                        download_items.c.error.is_not(None),
                    )
                )
                .order_by(download_items.c.id.asc())
                .limit(1)
            )
        )
        error_summary = None
        if failed_count:
            reason = first_error or "下载失败。"
            error_summary = reason if failed_count == 1 else f"{failed_count} 项失败: {reason}"
        connection.execute(
            update(download_jobs)
            .where(download_jobs.c.id == job_id)
            .values(
                state=state.value,
                finished_at=utc_now_text(),
                error_summary=error_summary,
            )
        )

    @staticmethod
    def _job_from_row(
        connection: object,
        row: RowMapping,
        include_items: bool,
    ) -> DownloadJobRecord:
        if include_items:
            item_rows = (
                connection.execute(
                    select(download_items)
                    .where(download_items.c.job_id == row["id"])
                    .order_by(download_items.c.id.asc())
                )
                .mappings()
                .all()
            )
            progress_row = next(
                (item for item in item_rows if string(item["state"]) == ItemState.RUNNING.value),
                None,
            )
            items = tuple(
                DownloadItemRecord(
                    item_id=integer(item["id"]),
                    artwork_id=integer(item["artwork_id"]),
                    state=ItemState(string(item["state"])),
                    attempts=integer(item["attempts"]),
                    error=optional_string(item["error"]),
                )
                for item in item_rows
            )
            counts = Counter(item.state for item in items)
        else:
            count_rows = connection.execute(
                select(download_items.c.state, func.count().label("item_count"))
                .where(download_items.c.job_id == row["id"])
                .group_by(download_items.c.state)
            ).all()
            items = ()
            counts = Counter({ItemState(string(item.state)): integer(item.item_count) for item in count_rows})
            progress_row = (
                connection.execute(
                    select(
                        download_items.c.artwork_id,
                        download_items.c.progress_phase,
                        download_items.c.progress_completed,
                        download_items.c.progress_total,
                    )
                    .where(
                        and_(
                            download_items.c.job_id == row["id"],
                            download_items.c.state == ItemState.RUNNING.value,
                        )
                    )
                    .limit(1)
                )
                .mappings()
                .first()
            )
        progress_phase = optional_string(progress_row["progress_phase"]) if progress_row is not None else None
        progress = (
            DownloadProgress(
                current_artwork_id=integer(progress_row["artwork_id"]),
                completed_pages=integer(progress_row["progress_completed"]),
                total_pages=optional_integer(progress_row["progress_total"]),
                phase=DownloadProgressPhase(progress_phase),
            )
            if progress_row is not None and progress_phase is not None
            else None
        )
        return DownloadJobRecord(
            job_id=string(row["id"]),
            source_label=string(row["source_label"]),
            state=JobState(string(row["state"])),
            cancel_requested=bool(row["cancel_requested"]),
            created_at=string(row["created_at"]),
            started_at=optional_string(row["started_at"]),
            finished_at=optional_string(row["finished_at"]),
            error_summary=optional_string(row["error_summary"]),
            counts=dict(counts),
            items=items if include_items else (),
            progress=progress,
        )
