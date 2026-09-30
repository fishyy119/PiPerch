from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from piperch.database import Database, run_migrations
from piperch.paths import AppPaths
from piperch.settings import SettingsManager

if TYPE_CHECKING:
    from pathlib import Path


def _manager(tmp_path: Path) -> tuple[AppPaths, Database, SettingsManager]:
    paths = AppPaths.from_data_dir(tmp_path / "settings")
    paths.ensure_directories()
    run_migrations(paths)
    database = Database(paths.database)
    return paths, database, SettingsManager(paths.settings, paths.default_library, database)


def test_initialize_creates_complete_default_settings(tmp_path: Path) -> None:
    paths, database, settings = _manager(tmp_path)
    try:
        settings.initialize()
        payload = json.loads(paths.settings.read_text(encoding="utf-8"))
    finally:
        database.close()

    assert payload == {
        "pixiv_cookie": None,
        "proxy_url": None,
        "library_root": str(paths.default_library),
        "download_concurrency": 3,
        "request_interval_ms": 500,
    }


def test_initialize_fills_and_persists_missing_values(tmp_path: Path) -> None:
    paths, database, settings = _manager(tmp_path)
    paths.settings.write_text('{"download_concurrency": 4}\n', encoding="utf-8")
    try:
        settings.initialize()
        current = settings.get()
        payload = json.loads(paths.settings.read_text(encoding="utf-8"))
    finally:
        database.close()

    assert current.download_concurrency == 4
    assert current.request_interval_ms == 500
    assert payload["library_root"] == str(paths.default_library)
    assert payload["request_interval_ms"] == 500
    assert "pixiv_cookie" in payload
    assert "proxy_url" in payload


def test_initialize_rejects_invalid_settings(tmp_path: Path) -> None:
    paths, database, settings = _manager(tmp_path)
    paths.settings.write_text('{"download_concurrency": "4"}\n', encoding="utf-8")
    try:
        with pytest.raises(ValidationError):
            settings.initialize()
    finally:
        database.close()
