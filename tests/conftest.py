from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from fastapi.testclient import TestClient

from piperch.app import create_app
from piperch.paths import AppPaths

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from piperch.container import AppContainer
    from tests.support import ApiTestClient


@pytest.fixture
def app_paths(tmp_path: Path) -> AppPaths:
    return AppPaths.from_data_dir(tmp_path / "data")


@pytest.fixture
def app_client(app_paths: AppPaths) -> Generator[tuple[ApiTestClient, AppContainer]]:
    app = create_app(app_paths)
    with TestClient(app) as client:
        container = cast("AppContainer", app.state.container)
        yield cast("ApiTestClient", client), container
