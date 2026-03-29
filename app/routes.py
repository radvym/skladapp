from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from .cart import add_to_cart, cart_count, clear_cart, get_cart, remove_from_cart, update_quantity
from .db import (
    create_reservation,
    get_item,
    get_reservation_by_code,
    init_request_db,
    list_items,
    log_reservation_event,
    register_rate_limit_event,
    update_webhook_status,
    get_db,
)
from .teams import build_payload, send_payload
from .validation import validate_checkout_form

bp = Blueprint("catalog", __name__)


@dataclass(slots=True)
class CartLine:
    item: dict[str, Any]
    quantity: int

    @property
    def subtotal(self) -> int:
        return self.quantity


@bp.before_app_request
def bind_database() -> None:
    init_request_db(current_app.config["DATABASE_PATH"])


@bp.app_context_processor
def inject_globals() -> dict[str, Any]:
    return {"cart_item_count": cart_count()}


@bp.route("/")
def index() -> str:
    connection = get_db()
    visibility = request.args.get("status", "available")
    items = list_items(connection)
    if visibility == "available":
        items = [item for item in items if item["status"] == "available"]
    elif visibility == "reserved":
        items = [item for item in items if item["status"] == "reserved"]
    return render_template("index.html", items=items, visibility=visibility)


@bp.route("/item/<slug>")
def item_detail(slug: str) -> str:
    item = get_item(get_db(), slug=slug)
    if not item or item["status"] == "hidden":
        abort(404)
    return render_template("detail.html", item=item)


@bp.route("/media/<variant>/<path:filename>")
def media_file(variant: str, filename: str):
    allowed_variants = {"thumb", "web", "detail", "originals"}
    if variant not in allowed_variants:
        abort(404)
    base_dir = Path(current_app.config["ORIGINALS_DIR"]) if variant == "originals" else Path(current_app.config["DERIVED_DIR"]) / variant
    return send_from_directory(str(base_dir.resolve()), filename)


@bp.post("/cart/add/<item_id>")
def cart_add(item_id: str):
    item = get_item(get_db(), item_id=item_id)
    if not item or item["status"] != "available":
        flash("Polozku uz nelze pridat do rezervace.", "error")
        return redirect(request.referrer or url_for("catalog.index"))
    add_to_cart(item)
    flash("Polozka byla pridana do rezervace.", "success")
    return redirect(request.referrer or url_for("catalog.cart_view"))


@bp.post("/cart/remove/<item_id>")
def cart_remove(item_id: str):
    remove_from_cart(item_id)
    flash("Polozka byla odebrana z rezervace.", "success")
    return redirect(url_for("catalog.cart_view"))


@bp.post("/cart/update/<item_id>")
def cart_update(item_id: str):
    item = get_item(get_db(), item_id=item_id)
    if not item:
        abort(404)
    quantity = max(0, int(request.form.get("quantity", "1")))
    update_quantity(item, quantity)
    flash("Kosik byl aktualizovan.", "success")
    return redirect(url_for("catalog.cart_view"))


@bp.route("/cart")
def cart_view() -> str:
    lines = _cart_lines()
    return render_template("cart.html", lines=lines)


@bp.route("/checkout", methods=["GET", "POST"])
def checkout() -> str:
    lines = _cart_lines()
    if not lines:
        flash("Rezervace je prazdna. Nejdriv pridejte alespon jednu polozku.", "error")
        return redirect(url_for("catalog.index"))

    if request.method == "GET":
        session["checkout_started_at"] = int(datetime.now(tz=timezone.utc).timestamp())
        return render_template("checkout.html", lines=lines, errors={}, form={})

    form, errors = validate_checkout_form(request.form)

    if not lines:
        errors["cart"] = "Rezervace je prazdna."

    if _submitted_too_fast(form.get("started_at")):
        errors["started_at"] = "Formular byl odeslan prilis rychle."

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    total = register_rate_limit_event(
        get_db(),
        ip_address,
        int(current_app.config["RATE_LIMIT_WINDOW_SECONDS"]),
    )
    if total > int(current_app.config["RATE_LIMIT_MAX_REQUESTS"]):
        errors["rate_limit"] = "Bylo odeslano prilis mnoho pozadavku. Zkuste to prosim pozdeji."

    if errors:
        return render_template("checkout.html", lines=lines, errors=errors, form=form), 400

    reservation_code = f"RZV-{secrets.token_hex(4).upper()}"
    reservation_items = []
    for line in lines:
        reservation_items.append(
            {
                "item_id": line.item["item_id"],
                "title": line.item["title"],
                "dimensions": line.item["dimensions"],
                "quantity": line.quantity,
                "url": url_for("catalog.item_detail", slug=line.item["slug"], _external=True),
            }
        )

    reservation_id = create_reservation(get_db(), reservation_code, form, reservation_items)
    reservation = get_reservation_by_code(get_db(), reservation_code)
    assert reservation is not None

    payload = build_payload(
        reservation,
        current_app.config["APP_BASE_URL"],
        current_app.config["TEAMS_WEBHOOK_MODE"],
    )

    webhook_url = current_app.config["TEAMS_WEBHOOK_URL"]
    if webhook_url:
        success, message = send_payload(webhook_url, payload)
        if success:
            update_webhook_status(get_db(), reservation_id, "sent")
            log_reservation_event(get_db(), reservation_id, "webhook_sent", message, payload)
        else:
            current_app.logger.error("Webhook delivery failed for %s: %s", reservation_code, message)
            update_webhook_status(get_db(), reservation_id, "failed", message)
            log_reservation_event(get_db(), reservation_id, "webhook_failed", message, payload)
    else:
        message = "Webhook URL neni nastavena."
        update_webhook_status(get_db(), reservation_id, "skipped", message)
        log_reservation_event(get_db(), reservation_id, "webhook_skipped", message, payload)

    clear_cart()
    flash("Rezervace byla prijata. Brzy se vam ozveme.", "success")
    return redirect(url_for("catalog.reservation_success", reservation_code=reservation_code))


@bp.route("/reservation/<reservation_code>")
def reservation_success(reservation_code: str) -> str:
    reservation = get_reservation_by_code(get_db(), reservation_code)
    if not reservation:
        abort(404)
    return render_template("success.html", reservation=reservation)


def _cart_lines() -> list[CartLine]:
    lines = []
    for item_id, quantity in get_cart().items():
        item = get_item(get_db(), item_id=item_id)
        if not item or item["status"] == "hidden":
            continue
        lines.append(CartLine(item=item, quantity=int(quantity)))
    return lines


def _submitted_too_fast(started_at_value: str | None) -> bool:
    if not started_at_value:
        return True
    try:
        started_at = int(started_at_value)
    except ValueError:
        return True
    now = int(datetime.now(tz=timezone.utc).timestamp())
    required_seconds = int(current_app.config["MIN_SUBMIT_SECONDS"])
    return (now - started_at) < required_seconds
