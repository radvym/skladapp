from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def load_catalog(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []

    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    items = payload.get("items", [])
    normalized = []
    used_ids: set[str] = set()

    for index, raw_item in enumerate(items):
        item_id = raw_item.get("id") or f"item-{index + 1:04d}"
        if item_id in used_ids:
            raise ValueError(f"Duplicate item id in catalog: {item_id}")
        used_ids.add(item_id)

        title = (raw_item.get("title") or item_id).strip()
        status = (raw_item.get("status") or "available").strip().lower()
        if status not in {"available", "reserved", "hidden"}:
            raise ValueError(f"Unsupported status '{status}' for item {item_id}")

        images = []
        for image in raw_item.get("images", []):
            basename = Path(image).name
            images.append(
                {
                    "source": image,
                    "basename": basename,
                    "alt": raw_item.get("image_alt") or title,
                }
            )

        normalized.append(
            {
                "item_id": item_id,
                "slug": slugify(raw_item.get("slug") or title or item_id),
                "title": title,
                "description": (raw_item.get("description") or "").strip(),
                "dimensions": (raw_item.get("dimensions") or "").strip(),
                "condition_note": (raw_item.get("condition_note") or "").strip(),
                "status": status,
                "is_unique": 1 if raw_item.get("is_unique", True) else 0,
                "images": images,
                "sort_order": int(raw_item.get("sort_order", index)),
            }
        )

    return normalized


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return normalized or "polozka"
