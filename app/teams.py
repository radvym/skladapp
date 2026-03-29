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
    item_lines = []

    for item in reservation["items"]:
        detail_url = item.get("item_url") or f"{app_base_url}/"
        item_line = f"- {item['title']} ({item['item_id']})"
        if item.get("dimensions"):
            item_line += f" | {item['dimensions']}"
        item_line += f" | {detail_url}"
        lines.append(item_line)
        item_lines.append(item_line)
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

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "msteams": {"width": "Full"},
        "body": [
            {
                "type": "TextBlock",
                "text": "Nova rezervace zbozi",
                "weight": "Bolder",
                "size": "Large",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": f"Rezervace {reservation['reservation_code']} prijata {timestamp}",
                "spacing": "None",
                "isSubtle": True,
                "wrap": True,
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Zakaznik", "value": customer_name},
                    {"title": "Mesto", "value": reservation["city"]},
                    {"title": "E-mail", "value": reservation["email"]},
                    {"title": "Telefon", "value": reservation["phone"]},
                ],
            },
            {
                "type": "TextBlock",
                "text": "Polozky",
                "weight": "Bolder",
                "wrap": True,
                "spacing": "Medium",
            },
            {
                "type": "TextBlock",
                "text": "\n".join(item_lines) if item_lines else "-",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": f"Poznamka: {note or '-'}",
                "wrap": True,
                "spacing": "Medium",
            },
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "Otevrit katalog",
                "url": app_base_url,
            }
        ],
    }


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
