from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image


def _safe_iso(dt: datetime | None) -> str:
    return dt.isoformat(timespec="seconds") if dt else ""


def _extract_exif_date(image: Image.Image) -> str:
    exif = image.getexif()
    if not exif:
        return ""

    for key, value in exif.items():
        tag_name = ExifTags.TAGS.get(key, key)
        if tag_name in {"DateTimeOriginal", "DateTime", "DateTimeDigitized"} and value:
            return str(value)
    return ""


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def average_hash_hex(image: Image.Image, hash_size: int = 8) -> str:
    grayscale = image.convert("L").resize((hash_size, hash_size))
    pixels = list(grayscale.getdata())
    if not pixels:
        return ""
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if pixel >= average else "0" for pixel in pixels)
    return f"{int(bits, 2):0{hash_size * hash_size // 4}x}"


def hamming_distance(left: str, right: str) -> int:
    if not left or not right:
        return 64
    left_bits = bin(int(left, 16))[2:].zfill(len(left) * 4)
    right_bits = bin(int(right, 16))[2:].zfill(len(right) * 4)
    return sum(a != b for a, b in zip(left_bits, right_bits))


def read_image_metadata(path: Path) -> dict[str, object]:
    stat = path.stat()
    with Image.open(path) as image:
        width, height = image.size
        exif_date = _extract_exif_date(image)
        perceptual_hash = average_hash_hex(image)

    created_at = datetime.fromtimestamp(stat.st_ctime)
    modified_at = datetime.fromtimestamp(stat.st_mtime)

    return {
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "file_size": stat.st_size,
        "file_created_at": _safe_iso(created_at),
        "file_modified_at": _safe_iso(modified_at),
        "image_width_px": width,
        "image_height_px": height,
        "exif_date": exif_date,
        "hash": sha256_for_file(path),
        "perceptual_hash": perceptual_hash,
    }
