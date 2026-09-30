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
    frontend_dist: Path

    @classmethod
    def from_data_dir(cls, data_dir: Path | None = None) -> AppPaths:
        root = (data_dir or Path.home() / ".piperch").expanduser().resolve()
        project_root = Path(__file__).resolve().parents[2]
        return cls(
            data_dir=root,
            database=root / "piperch.sqlite3",
            settings=root / "settings.json",
            default_library=root / "library",
            thumbnails=root / "cache" / "thumbnails",
            staging=root / "staging",
            frontend_dist=project_root / "frontend" / "dist",
        )

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.default_library,
            self.thumbnails,
            self.staging,
        ):
            path.mkdir(parents=True, exist_ok=True)
