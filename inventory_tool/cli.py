from __future__ import annotations

import argparse
from pathlib import Path

from inventory_tool.config import AppConfig
from inventory_tool.pipeline import run_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export inventory records from storage photos.")
    parser.add_argument("--input", required=True, help="Input directory with photos.")
    parser.add_argument("--output", required=True, help="Output XLSX file path.")
    parser.add_argument("--csv", help="Optional CSV output path.")
    parser.add_argument("--config", help="Optional JSON config file.")
    parser.add_argument("--recursive", action="store_true", help="Scan input directory recursively.")
    parser.add_argument(
        "--ocr",
        choices=["on", "off", "auto"],
        default=None,
        help="OCR mode. Defaults to config value or auto.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    csv_path = Path(args.csv).expanduser().resolve() if args.csv else output_path.with_suffix(".csv")
    config_path = Path(args.config).expanduser().resolve() if args.config else None

    config = AppConfig.from_file(config_path).merge_overrides(
        recursive=True if args.recursive else None,
        ocr_mode=args.ocr,
    )

    if not input_dir.exists() or not input_dir.is_dir():
        parser.error(f"Input directory does not exist: {input_dir}")

    run_inventory(
        input_dir=input_dir,
        xlsx_output=output_path,
        csv_output=csv_path,
        config=config,
    )
    print(f"XLSX export created: {output_path}")
    print(f"CSV export created: {csv_path}")
    return 0
