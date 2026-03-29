from __future__ import annotations

import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from .catalog import load_catalog, slugify
from .db import SCHEMA, upsert_items

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - exercised only in environments without Pillow
    Image = None
    ImageOps = None


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DERIVED_VARIANTS = {
    "thumb": {"width": 420, "quality": 78},
    "web": {"width": 1280, "quality": 82},
    "detail": {"width": 1800, "quality": 88},
}


def import_catalog(
    catalog_path: Path,
    originals_dir: Path,
    derived_dir: Path,
    database_path: Path,
    source_dir: Path | None = None,
) -> list[dict[str, Any]]:
    originals_dir.mkdir(parents=True, exist_ok=True)
    derived_dir.mkdir(parents=True, exist_ok=True)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if source_dir:
        sync_originals(source_dir, originals_dir)

    catalog_items = load_catalog(catalog_path)
    items = add_automatic_items(catalog_items, originals_dir)
    generate_derived_images(originals_dir, derived_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        upsert_items(connection, items)
    finally:
        connection.close()
    return items


def sync_originals(source_dir: Path, originals_dir: Path) -> None:
    for image_path in sorted(source_dir.iterdir()):
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS or not image_path.is_file():
            continue
        target = originals_dir / image_path.name
        if not target.exists():
            shutil.copy2(image_path, target)


def add_automatic_items(catalog_items: list[dict[str, Any]], originals_dir: Path) -> list[dict[str, Any]]:
    used_images = {
        image["basename"]
        for item in catalog_items
        for image in item.get("images", [])
    }
    items = list(catalog_items)

    for image_path in sorted(originals_dir.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if image_path.name in used_images:
            continue
        item_id = f"auto-{image_path.stem.lower()}"
        title = f"Skladovy kus {image_path.stem}"
        items.append(
            {
                "item_id": item_id,
                "slug": slugify(title),
                "title": title,
                "description": "",
                "dimensions": "",
                "condition_note": "Automaticky vytvorena polozka bez doplnenych metadat.",
                "status": "available",
                "is_unique": 1,
                "images": [
                    {
                        "source": image_path.name,
                        "basename": image_path.name,
                        "alt": title,
                    }
                ],
                "sort_order": 10_000 + len(items),
            }
        )
    return items


def generate_derived_images(originals_dir: Path, derived_dir: Path) -> None:
    for image_path in sorted(originals_dir.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        for variant_name, options in DERIVED_VARIANTS.items():
            variant_dir = derived_dir / variant_name
            variant_dir.mkdir(parents=True, exist_ok=True)
            webp_target = variant_dir / f"{image_path.stem}.webp"
            jpeg_target = variant_dir / f"{image_path.stem}.jpg"
            _build_variant(image_path, webp_target, jpeg_target, options["width"], options["quality"])


def _build_variant(
    source: Path,
    webp_target: Path,
    jpeg_target: Path,
    width: int,
    quality: int,
) -> None:
    if Image is not None:
        _build_with_pillow(source, webp_target, jpeg_target, width, quality)
        return

    if shutil.which("sips"):
        _build_with_sips(source, webp_target, jpeg_target, width, quality)
        return

    raise RuntimeError(
        "Image processing requires Pillow or macOS sips. Install Pillow with 'pip install Pillow'."
    )


def _build_with_pillow(source: Path, webp_target: Path, jpeg_target: Path, width: int, quality: int) -> None:
    assert Image is not None
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        resized = image.copy()
        resized.thumbnail((width, width * 2))
        resized.save(webp_target, format="WEBP", quality=quality, method=6)
        resized.save(jpeg_target, format="JPEG", quality=quality, optimize=True, progressive=True)


def _build_with_sips(source: Path, webp_target: Path, jpeg_target: Path, width: int, quality: int) -> None:
    png_target = webp_target.with_suffix(".png")
    subprocess.run(
        ["sips", "-Z", str(width), str(source), "--out", str(png_target)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["sips", "-s", "format", "jpeg", str(png_target), "--out", str(jpeg_target)],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        subprocess.run(
            ["sips", "-s", "format", "webp", str(source), "--out", str(webp_target)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["sips", "-Z", str(width), str(webp_target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        pass
    if png_target.exists():
        png_target.unlink()
