#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import dotenv_values

from app.db import list_pending_webhooks, log_reservation_event, update_webhook_status
from app.teams import build_payload, send_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zkusi znovu odeslat neodeslane webhooky.")
    parser.add_argument("--database", default="data/app.db", help="SQLite databaze aplikace.")
    parser.add_argument("--env-file", default=".env", help="Cesta k .env konfiguraci.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = dotenv_values(args.env_file)
    webhook_url = (env.get("TEAMS_WEBHOOK_URL") or "").strip()
    app_base_url = (env.get("APP_BASE_URL") or "http://127.0.0.1:5000").rstrip("/")
    webhook_mode = (env.get("TEAMS_WEBHOOK_MODE") or "workflow").strip().lower()

    if not webhook_url:
        print("TEAMS_WEBHOOK_URL is not set.")
        return 1

    connection = sqlite3.connect(Path(args.database))
    connection.row_factory = sqlite3.Row

    sent_count = 0
    failed_count = 0
    try:
        for reservation in list_pending_webhooks(connection):
            payload = build_payload(reservation, app_base_url, webhook_mode)
            success, message = send_payload(webhook_url, payload)
            if success:
                update_webhook_status(connection, reservation["id"], "sent")
                log_reservation_event(connection, reservation["id"], "webhook_sent_retry", message, payload)
                sent_count += 1
            else:
                update_webhook_status(connection, reservation["id"], "failed", message)
                log_reservation_event(connection, reservation["id"], "webhook_failed_retry", message, payload)
                failed_count += 1
    finally:
        connection.close()

    print(f"Retried webhooks. Sent: {sent_count}, failed: {failed_count}.")
    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
