from __future__ import annotations

import json
from typing import TYPE_CHECKING

from piperch.paths import AppPaths
from piperch.settings import SettingsManager

if TYPE_CHECKING:
    from pathlib import Path


def _manager(tmp_path: Path) -> tuple[AppPaths, SettingsManager]:
    paths = AppPaths.from_data_dir(tmp_path / "settings")
    paths.ensure_directories()
    return paths, SettingsManager(paths.settings, paths.default_library)


def test_initialize_persists_default_settings(tmp_path: Path) -> None:
    paths, settings = _manager(tmp_path)
    settings.initialize()
    current = settings.get()
    payload = json.loads(paths.settings.read_text(encoding="utf-8"))

    assert current.library_root == paths.default_library
    assert payload == current.model_dump(mode="json")


def test_initialize_fills_and_persists_missing_values(tmp_path: Path) -> None:
    paths, settings = _manager(tmp_path)
    paths.settings.write_text('{"download_concurrency": 4}\n', encoding="utf-8")
    settings.initialize()
    current = settings.get()
    payload = json.loads(paths.settings.read_text(encoding="utf-8"))

    assert current.download_concurrency == 4
    assert payload["library_root"] == str(paths.default_library)
    assert payload == current.model_dump(mode="json")
