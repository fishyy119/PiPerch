from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    data_dir: Path
    database: Path
    settings: Path
    default_library: Path
    thumbnails: Path
    staging: Path
    storage_migration: Path

    @classmethod
    def from_data_dir(cls, data_dir: Path | None = None) -> AppPaths:
        root = (data_dir or Path.home() / ".piperch").expanduser().resolve()
        return cls(
            data_dir=root,
            database=root / "piperch.sqlite3",
            settings=root / "settings.json",
            default_library=root / "library",
            thumbnails=root / "cache" / "thumbnails",
            staging=root / "staging",
            storage_migration=root / "storage-migration.json",
        )

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.thumbnails,
            self.staging,
        ):
            path.mkdir(parents=True, exist_ok=True)
