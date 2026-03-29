from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


@dataclass(slots=True)
class AppConfig:
    supported_extensions: list[str] = field(default_factory=lambda: list(DEFAULT_EXTENSIONS))
    recursive: bool = False
    ocr_mode: str = "auto"
    duplicate_threshold: int = 4
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def from_file(cls, path: Path | None) -> "AppConfig":
        config = cls()
        if path is None:
            return config

        payload = json.loads(path.read_text(encoding="utf-8"))
        for key, value in payload.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config

    def merge_overrides(self, *, recursive: bool | None = None, ocr_mode: str | None = None) -> "AppConfig":
        return AppConfig(
            supported_extensions=list(self.supported_extensions),
            recursive=self.recursive if recursive is None else recursive,
            ocr_mode=self.ocr_mode if ocr_mode is None else ocr_mode,
            duplicate_threshold=self.duplicate_threshold,
            timestamp_format=self.timestamp_format,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "supported_extensions": self.supported_extensions,
            "recursive": self.recursive,
            "ocr_mode": self.ocr_mode,
            "duplicate_threshold": self.duplicate_threshold,
            "timestamp_format": self.timestamp_format,
        }
