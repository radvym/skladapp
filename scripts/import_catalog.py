#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.importer import import_catalog


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import skladovych fotek a metadat do katalogu.")
    parser.add_argument("--catalog", default="data/catalog.yaml", help="Cesta ke katalogovemu YAML souboru.")
    parser.add_argument("--source-dir", default=None, help="Volitelna zdrojova slozka s puvodnimi obrazky.")
    parser.add_argument("--originals-dir", default="media/originals", help="Slozka pro originaly.")
    parser.add_argument("--derived-dir", default="media/derived", help="Slozka pro optimalizovane obrazky.")
    parser.add_argument("--database", default="data/app.db", help="SQLite databaze aplikace.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    items = import_catalog(
        catalog_path=Path(args.catalog),
        originals_dir=Path(args.originals_dir),
        derived_dir=Path(args.derived_dir),
        database_path=Path(args.database),
        source_dir=Path(args.source_dir) if args.source_dir else None,
    )
    print(f"Imported {len(items)} catalog items.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
