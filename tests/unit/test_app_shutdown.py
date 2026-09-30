from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest

from piperch.app import shutdown_resources

if TYPE_CHECKING:
    from piperch.database import Database
    from piperch.pixiv import PixivClient
    from piperch.services.downloads import DownloadSupervisor


class SlowSupervisor:
    def __init__(self) -> None:
        self.cancelled = False

    async def stop(self) -> None:
        try:
            await asyncio.Event().wait()
        finally:
            self.cancelled = True


class ClosingPixiv:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class ClosingDatabase:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_shutdown_timeout_does_not_skip_remaining_resources() -> None:
    supervisor = SlowSupervisor()
    pixiv = ClosingPixiv()
    database = ClosingDatabase()

    await shutdown_resources(
        cast("DownloadSupervisor", supervisor),
        cast("PixivClient", pixiv),
        cast("Database", database),
        supervisor_timeout_seconds=0.01,
        http_timeout_seconds=0.01,
    )

    assert supervisor.cancelled
    assert pixiv.closed
    assert database.closed
