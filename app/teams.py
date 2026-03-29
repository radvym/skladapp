from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib import error, request


def build_payload(
    reservation: dict[str, Any],
    app_base_url: str,
    mode: str = "workflow",
) -> dict[str, Any]:
    timestamp = _format_timestamp(reservation["created_at"])
    customer_name = f"{reservation['first_name']} {reservation['last_name']}"
    lines = [
        "## Nova rezervace zbozi",
        "",
        f"**Datum:** {timestamp}",
        f"**Zakaznik:** {customer_name}",
        f"**Mesto:** {reservation['city']}",
        f"**E-mail:** {reservation['email']}",
        f"**Telefon:** {reservation['phone']}",
        "",
        "**Polozky:**",
    ]
    items = []
    facts = []

    for item in reservation["items"]:
        detail_url = item.get("item_url") or f"{app_base_url}/"
        item_line = f"- {item['title']} ({item['item_id']})"
        if item.get("dimensions"):
            item_line += f" | {item['dimensions']}"
        item_line += f" | {detail_url}"
        lines.append(item_line)
        items.append(
            {
                "item_id": item["item_id"],
                "title": item["title"],
                "dimensions": item.get("dimensions", ""),
                "quantity": item.get("quantity", 1),
                "detail_url": detail_url,
            }
        )
        facts.append(
            {
                "name": item["item_id"],
                "value": f"{item['title']} | {item.get('dimensions', '')} | {detail_url}",
            }
        )

    note = reservation.get("note", "").strip()
    lines.extend(["", f"**Poznamka:** {note or '-'}"])

    workflow_payload = {
        "title": "Nova rezervace zbozi",
        "submitted_at": reservation["created_at"],
        "reservation_code": reservation["reservation_code"],
        "customer": {
            "first_name": reservation["first_name"],
            "last_name": reservation["last_name"],
            "city": reservation["city"],
            "email": reservation["email"],
            "phone": reservation["phone"],
        },
        "items": items,
        "note": note,
        "summary_markdown": "\n".join(lines),
        "catalog_url": app_base_url,
    }

    if mode == "incoming":
        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": "0078D4",
            "summary": "Nova rezervace zbozi",
            "title": "Nova rezervace zbozi",
            "sections": [
                {
                    "activityTitle": f"Rezervace {reservation['reservation_code']}",
                    "facts": [
                        {"name": "Datum", "value": timestamp},
                        {"name": "Zakaznik", "value": customer_name},
                        {"name": "Mesto", "value": reservation["city"]},
                        {"name": "E-mail", "value": reservation["email"]},
                        {"name": "Telefon", "value": reservation["phone"]},
                        *facts,
                        {"name": "Poznamka", "value": note or "-"},
                    ],
                    "markdown": True,
                }
            ],
        }

    return workflow_payload


def send_payload(webhook_url: str, payload: dict[str, Any], timeout: int = 10) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            status_code = getattr(response, "status", 200)
            response_body = response.read().decode("utf-8", errors="replace")
        if 200 <= status_code < 300:
            return True, response_body[:500]
        return False, f"Webhook returned HTTP {status_code}: {response_body[:500]}"
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, f"Webhook HTTP error {exc.code}: {body[:500]}"
    except error.URLError as exc:
        return False, f"Webhook URL error: {exc.reason}"
    except Exception as exc:  # pragma: no cover - defensive guard
        return False, f"Unexpected webhook error: {exc}"


def _format_timestamp(value: str) -> str:
    dt = datetime.fromisoformat(value)
    return dt.strftime("%d.%m.%Y %H:%M")
