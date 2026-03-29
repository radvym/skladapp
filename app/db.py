from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import Flask, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    dimensions TEXT NOT NULL DEFAULT '',
    condition_note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'available',
    is_unique INTEGER NOT NULL DEFAULT 1,
    images_json TEXT NOT NULL,
    primary_image TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    city TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'received',
    webhook_status TEXT NOT NULL DEFAULT 'pending',
    webhook_error TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reservation_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    dimensions TEXT NOT NULL DEFAULT '',
    quantity INTEGER NOT NULL DEFAULT 1,
    item_url TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reservation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER REFERENCES reservations(id) ON DELETE CASCADE,
    log_type TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_limit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def ensure_database(app: Flask) -> None:
    database_path = Path(app.config["DATABASE_PATH"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(g.get("_database_path"))
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def init_request_db(database_path: str) -> None:
    g._database_path = database_path


def close_db(_: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
    g.pop("_database_path", None)


def upsert_items(connection: sqlite3.Connection, items: list[dict[str, Any]]) -> None:
    now = utcnow().isoformat()
    connection.executemany(
        """
        INSERT INTO items (
            item_id, slug, title, description, dimensions, condition_note,
            status, is_unique, images_json, primary_image, sort_order, updated_at
        ) VALUES (
            :item_id, :slug, :title, :description, :dimensions, :condition_note,
            :status, :is_unique, :images_json, :primary_image, :sort_order, :updated_at
        )
        ON CONFLICT(item_id) DO UPDATE SET
            slug=excluded.slug,
            title=excluded.title,
            description=excluded.description,
            dimensions=excluded.dimensions,
            condition_note=excluded.condition_note,
            status=CASE
                WHEN items.status = 'reserved' AND excluded.status = 'available' THEN items.status
                ELSE excluded.status
            END,
            is_unique=excluded.is_unique,
            images_json=excluded.images_json,
            primary_image=excluded.primary_image,
            sort_order=excluded.sort_order,
            updated_at=excluded.updated_at
        """,
        [
            {
                **item,
                "images_json": json.dumps(item["images"], ensure_ascii=False),
                "primary_image": item["images"][0]["basename"] if item["images"] else "",
                "updated_at": now,
            }
            for item in items
        ],
    )
    connection.commit()


def list_items(connection: sqlite3.Connection, include_hidden: bool = False) -> list[dict[str, Any]]:
    query = """
        SELECT item_id, slug, title, description, dimensions, condition_note,
               status, is_unique, images_json, primary_image, sort_order, updated_at
        FROM items
    """
    params: tuple[Any, ...] = ()
    if not include_hidden:
        query += " WHERE status != ?"
        params = ("hidden",)
    query += " ORDER BY sort_order ASC, title COLLATE NOCASE ASC"
    rows = connection.execute(query, params).fetchall()
    return [_row_to_item(row) for row in rows]


def get_item(connection: sqlite3.Connection, item_id: str | None = None, slug: str | None = None) -> dict[str, Any] | None:
    if item_id:
        row = connection.execute(
            """
            SELECT item_id, slug, title, description, dimensions, condition_note,
                   status, is_unique, images_json, primary_image, sort_order, updated_at
            FROM items WHERE item_id = ?
            """,
            (item_id,),
        ).fetchone()
    elif slug:
        row = connection.execute(
            """
            SELECT item_id, slug, title, description, dimensions, condition_note,
                   status, is_unique, images_json, primary_image, sort_order, updated_at
            FROM items WHERE slug = ?
            """,
            (slug,),
        ).fetchone()
    else:
        return None
    return _row_to_item(row) if row else None


def set_item_status(connection: sqlite3.Connection, item_id: str, status: str) -> bool:
    cursor = connection.execute(
        "UPDATE items SET status = ?, updated_at = ? WHERE item_id = ?",
        (status, utcnow().isoformat(), item_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def set_items_reserved(connection: sqlite3.Connection, item_ids: list[str]) -> None:
    if not item_ids:
        return
    placeholders = ",".join("?" for _ in item_ids)
    params = ["reserved", utcnow().isoformat(), *item_ids]
    connection.execute(
        f"UPDATE items SET status = ?, updated_at = ? WHERE item_id IN ({placeholders})",
        params,
    )
    connection.commit()


def create_reservation(
    connection: sqlite3.Connection,
    reservation_code: str,
    customer: dict[str, str],
    items: list[dict[str, Any]],
) -> int:
    created_at = utcnow().isoformat()
    cursor = connection.execute(
        """
        INSERT INTO reservations (
            reservation_code, created_at, first_name, last_name, city, email, phone, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reservation_code,
            created_at,
            customer["first_name"],
            customer["last_name"],
            customer["city"],
            customer["email"],
            customer["phone"],
            customer["note"],
        ),
    )
    reservation_id = cursor.lastrowid
    connection.executemany(
        """
        INSERT INTO reservation_items (reservation_id, item_id, title, dimensions, quantity, item_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                reservation_id,
                item["item_id"],
                item["title"],
                item["dimensions"],
                item["quantity"],
                item.get("url", ""),
            )
            for item in items
        ],
    )
    connection.commit()
    return int(reservation_id)


def log_reservation_event(
    connection: sqlite3.Connection,
    reservation_id: int,
    log_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO reservation_logs (reservation_id, log_type, message, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id,
            log_type,
            message,
            json.dumps(payload or {}, ensure_ascii=False),
            utcnow().isoformat(),
        ),
    )
    connection.commit()


def update_webhook_status(
    connection: sqlite3.Connection,
    reservation_id: int,
    status: str,
    error_message: str = "",
) -> None:
    connection.execute(
        "UPDATE reservations SET webhook_status = ?, webhook_error = ? WHERE id = ?",
        (status, error_message, reservation_id),
    )
    connection.commit()


def get_reservation_by_code(connection: sqlite3.Connection, reservation_code: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, reservation_code, created_at, first_name, last_name, city, email, phone,
               note, status, webhook_status, webhook_error
        FROM reservations WHERE reservation_code = ?
        """,
        (reservation_code,),
    ).fetchone()
    if not row:
        return None
    items = connection.execute(
        """
        SELECT item_id, title, dimensions, quantity, item_url
        FROM reservation_items
        WHERE reservation_id = ?
        ORDER BY id ASC
        """,
        (row["id"],),
    ).fetchall()
    payload = dict(row)
    payload["items"] = [dict(item) for item in items]
    return payload


def list_pending_webhooks(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, reservation_code, created_at, first_name, last_name, city, email, phone,
               note, status, webhook_status, webhook_error
        FROM reservations
        WHERE webhook_status IN ('pending', 'failed')
        ORDER BY created_at ASC
        """
    ).fetchall()
    reservations = []
    for row in rows:
        reservation = dict(row)
        reservation["items"] = [
            dict(item)
            for item in connection.execute(
                """
                SELECT item_id, title, dimensions, quantity, item_url
                FROM reservation_items
                WHERE reservation_id = ?
                ORDER BY id ASC
                """,
                (row["id"],),
            ).fetchall()
        ]
        reservations.append(reservation)
    return reservations


def register_rate_limit_event(connection: sqlite3.Connection, ip_address: str, window_seconds: int) -> int:
    cutoff = (utcnow() - timedelta(seconds=window_seconds)).isoformat()
    connection.execute(
        "DELETE FROM rate_limit_events WHERE created_at < ?",
        (cutoff,),
    )
    connection.execute(
        "INSERT INTO rate_limit_events (ip_address, created_at) VALUES (?, ?)",
        (ip_address, utcnow().isoformat()),
    )
    connection.commit()
    row = connection.execute(
        "SELECT COUNT(*) AS total FROM rate_limit_events WHERE ip_address = ? AND created_at >= ?",
        (ip_address, cutoff),
    ).fetchone()
    return int(row["total"])


def _row_to_item(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        return {}
    item = dict(row)
    item["images"] = json.loads(item.pop("images_json"))
    item["is_unique"] = bool(item["is_unique"])
    return item


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
