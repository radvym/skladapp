from __future__ import annotations

from pathlib import Path


def discover_images(input_dir: Path, supported_extensions: list[str], recursive: bool) -> list[Path]:
    extensions = {ext.lower() for ext in supported_extensions}
    iterator = input_dir.rglob("*") if recursive else input_dir.iterdir()
    files = [
        path
        for path in iterator
        if path.is_file() and path.suffix.lower() in extensions
    ]
    return sorted(files, key=lambda path: path.name.lower())
