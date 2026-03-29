#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import set_item_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zmeni stav polozky v SQLite katalogu.")
    parser.add_argument("item_id", help="ID polozky.")
    parser.add_argument("status", choices=["available", "reserved", "hidden"], help="Novy stav.")
    parser.add_argument("--database", default="data/app.db", help="SQLite databaze aplikace.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    connection = sqlite3.connect(Path(args.database))
    try:
        updated = set_item_status(connection, args.item_id, args.status)
    finally:
        connection.close()

    if not updated:
        print(f"Item '{args.item_id}' was not found.")
        return 1
    print(f"Item '{args.item_id}' updated to '{args.status}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
