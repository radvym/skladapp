from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any


SERIAL_PATTERN = re.compile(r"\b[A-Z0-9][A-Z0-9\-/]{4,}\b")


def choose_label_text(ocr_text: str) -> str:
    if not ocr_text:
        return ""
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    if not lines:
        return ""
    return " | ".join(lines[:3])[:500]


def infer_title(ocr_text: str) -> str:
    if not ocr_text:
        return ""

    candidates = []
    for line in ocr_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) > 60:
            continue
        if len(line.split()) > 8:
            continue
        candidates.append(line)

    return candidates[0][:120] if candidates else ""


def detect_metadata_tokens(ocr_text: str) -> str:
    if not ocr_text:
        return ""

    tokens = SERIAL_PATTERN.findall(ocr_text.upper())
    if not tokens:
        return ""

    deduplicated: list[str] = []
    seen = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduplicated.append(token)
    return ", ".join(deduplicated[:10])


def infer_tags(ocr_text: str) -> tuple[str, str, str]:
    if not ocr_text:
        return "", "", ""

    words = [
        word.lower()
        for word in re.findall(r"[A-Za-zÀ-ž0-9]{4,}", ocr_text)
        if not word.isdigit()
    ]
    counts = Counter(words)
    tags = [word for word, _ in counts.most_common(3)]
    tags += [""] * (3 - len(tags))
    return tags[0], tags[1], tags[2]


def infer_confidence(*, ocr_text: str, dimensions_raw: str, label_text: str, duplicate_suspected: bool) -> str:
    score = 0
    if ocr_text:
        score += 1
    if label_text:
        score += 1
    if dimensions_raw:
        score += 1
    if duplicate_suspected:
        score -= 1

    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def infer_status(*, ocr_used: bool, ocr_text: str, manual_review_required: bool) -> str:
    if not ocr_used:
        return "ocr_unavailable"
    if manual_review_required:
        return "needs_review"
    if not ocr_text:
        return "no_text"
    return "ok"


def build_record(
    *,
    index: int,
    metadata: dict[str, Any],
    ocr_text: str,
    dimensions: dict[str, Any],
    duplicate_group: str,
    duplicate_suspected: bool,
    ocr_used: bool,
) -> dict[str, Any]:
    item_id = f"ITEM-{index:06d}"
    photo_id = f"PHOTO-{index:06d}"
    label_text = choose_label_text(ocr_text)
    title = infer_title(ocr_text)
    detected_metadata = detect_metadata_tokens(ocr_text)
    tag_1, tag_2, tag_3 = infer_tags(ocr_text)
    manual_review_required = not ocr_text or duplicate_suspected or not dimensions["dimensions_raw"]
    confidence = infer_confidence(
        ocr_text=ocr_text,
        dimensions_raw=str(dimensions["dimensions_raw"]),
        label_text=label_text,
        duplicate_suspected=duplicate_suspected,
    )
    status = infer_status(
        ocr_used=ocr_used,
        ocr_text=ocr_text,
        manual_review_required=manual_review_required,
    )
    created_at = datetime.now().isoformat(timespec="seconds")

    return {
        "item_id": item_id,
        "source_image": metadata["file_name"],
        "photo_id": photo_id,
        "file_name": metadata["file_name"],
        "file_path": metadata["file_path"],
        "detected_count_on_image": 1 if ocr_text else "",
        "title": title or item_id,
        "description": label_text[:250] if label_text else "",
        "dimensions_raw": dimensions["dimensions_raw"],
        "width": dimensions["width"],
        "height": dimensions["height"],
        "depth": dimensions["depth"],
        "dimension_unit": dimensions["dimension_unit"],
        "label_text": label_text,
        "detected_metadata": detected_metadata,
        "notes": "" if ocr_text else "No OCR text detected or OCR disabled.",
        "confidence": confidence,
        "status": status,
        "created_at": created_at,
        "image_width_px": metadata["image_width_px"],
        "image_height_px": metadata["image_height_px"],
        "file_size": metadata["file_size"],
        "file_created_at": metadata["file_created_at"],
        "file_modified_at": metadata["file_modified_at"],
        "exif_date": metadata["exif_date"],
        "hash": metadata["hash"],
        "perceptual_hash": metadata["perceptual_hash"],
        "duplicate_group": duplicate_group,
        "duplicate_suspected": duplicate_suspected,
        "category": "",
        "tag_1": tag_1,
        "tag_2": tag_2,
        "tag_3": tag_3,
        "manual_review_required": manual_review_required,
        "ocr_used": ocr_used,
        "ocr_text_raw": ocr_text,
        "hyperlink": metadata["file_path"],
    }
