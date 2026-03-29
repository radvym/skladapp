from __future__ import annotations

from pathlib import Path

import pandas as pd

from inventory_tool.config import AppConfig
from inventory_tool.dimensions import parse_dimensions
from inventory_tool.exporters import INVENTORY_COLUMNS, build_summary, export_csv, export_xlsx
from inventory_tool.file_loader import discover_images
from inventory_tool.metadata import hamming_distance, read_image_metadata
from inventory_tool.ocr import extract_text, is_tesseract_available
from inventory_tool.records import build_record


def _duplicate_groups(metadata_rows: list[dict[str, object]], threshold: int) -> list[tuple[str, bool]]:
    groups: list[str] = []
    suspects: list[bool] = []
    known_hashes: list[str] = []

    for index, metadata in enumerate(metadata_rows, start=1):
        current_hash = str(metadata["perceptual_hash"])
        assigned_group = f"DUP-{index:04d}"
        duplicate_suspected = False

        for previous_index, previous_hash in enumerate(known_hashes, start=1):
            if hamming_distance(current_hash, previous_hash) <= threshold:
                assigned_group = f"DUP-{previous_index:04d}"
                duplicate_suspected = True
                break

        groups.append(assigned_group)
        suspects.append(duplicate_suspected)
        known_hashes.append(current_hash)

    return list(zip(groups, suspects))


def run_inventory(
    *,
    input_dir: Path,
    xlsx_output: Path,
    csv_output: Path | None,
    config: AppConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    images = discover_images(input_dir, config.supported_extensions, config.recursive)
    metadata_rows = [read_image_metadata(path) for path in images]
    duplicate_info = _duplicate_groups(metadata_rows, config.duplicate_threshold)

    use_ocr = config.ocr_mode == "on" or (config.ocr_mode == "auto" and is_tesseract_available())
    records: list[dict[str, object]] = []

    for index, metadata in enumerate(metadata_rows, start=1):
        image_path = Path(str(metadata["file_path"]))
        ocr_text = extract_text(image_path) if use_ocr else ""
        dimensions = parse_dimensions(ocr_text)
        duplicate_group, duplicate_suspected = duplicate_info[index - 1]
        record = build_record(
            index=index,
            metadata=metadata,
            ocr_text=ocr_text,
            dimensions=dimensions,
            duplicate_group=duplicate_group,
            duplicate_suspected=duplicate_suspected,
            ocr_used=use_ocr,
        )
        records.append(record)

    dataframe = pd.DataFrame(records, columns=INVENTORY_COLUMNS)
    summary = build_summary(records, len(images))
    export_xlsx(dataframe, summary, xlsx_output)
    if csv_output:
        export_csv(dataframe, csv_output)
    return dataframe, summary
