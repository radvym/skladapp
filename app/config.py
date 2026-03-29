from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    base_dir: Path
    secret_key: str
    database_path: Path
    media_root: Path
    originals_dir: Path
    derived_dir: Path
    data_dir: Path
    logs_dir: Path
    log_path: Path
    catalog_path: Path
    app_base_url: str
    teams_webhook_url: str
    teams_webhook_mode: str
    rate_limit_window_seconds: int
    rate_limit_max_requests: int
    min_submit_seconds: int

    @classmethod
    def from_env(cls) -> "Config":
        base_dir = Path(__file__).resolve().parent.parent
        load_dotenv(base_dir / ".env")

        data_dir = base_dir / "data"
        media_root = Path(os.getenv("MEDIA_ROOT", base_dir / "media"))
        logs_dir = base_dir / "logs"

        return cls(
            base_dir=base_dir,
            secret_key=os.getenv("SECRET_KEY", "change-me"),
            database_path=Path(os.getenv("DATABASE_PATH", data_dir / "app.db")),
            media_root=media_root,
            originals_dir=media_root / "originals",
            derived_dir=media_root / "derived",
            data_dir=data_dir,
            logs_dir=logs_dir,
            log_path=Path(os.getenv("LOG_PATH", logs_dir / "app.log")),
            catalog_path=Path(os.getenv("CATALOG_PATH", data_dir / "catalog.yaml")),
            app_base_url=os.getenv("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/"),
            teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL", ""),
            teams_webhook_mode=os.getenv("TEAMS_WEBHOOK_MODE", "workflow").strip().lower(),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "900")),
            rate_limit_max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "5")),
            min_submit_seconds=int(os.getenv("MIN_SUBMIT_SECONDS", "2")),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "SECRET_KEY": self.secret_key,
            "DATABASE_PATH": str(self.database_path),
            "MEDIA_ROOT": str(self.media_root),
            "ORIGINALS_DIR": str(self.originals_dir),
            "DERIVED_DIR": str(self.derived_dir),
            "DATA_DIR": str(self.data_dir),
            "LOGS_DIR": str(self.logs_dir),
            "LOG_PATH": str(self.log_path),
            "CATALOG_PATH": str(self.catalog_path),
            "APP_BASE_URL": self.app_base_url,
            "TEAMS_WEBHOOK_URL": self.teams_webhook_url,
            "TEAMS_WEBHOOK_MODE": self.teams_webhook_mode,
            "RATE_LIMIT_WINDOW_SECONDS": self.rate_limit_window_seconds,
            "RATE_LIMIT_MAX_REQUESTS": self.rate_limit_max_requests,
            "MIN_SUBMIT_SECONDS": self.min_submit_seconds,
        }
