from __future__ import annotations

from typing import Any

from flask import session


def get_cart() -> dict[str, int]:
    return session.setdefault("cart", {})


def add_to_cart(item: dict[str, Any], quantity: int = 1) -> None:
    cart = get_cart()
    current = int(cart.get(item["item_id"], 0))
    if item["is_unique"]:
        cart[item["item_id"]] = 1
    else:
        cart[item["item_id"]] = max(1, current + quantity)
    session.modified = True


def remove_from_cart(item_id: str) -> None:
    cart = get_cart()
    cart.pop(item_id, None)
    session.modified = True


def update_quantity(item: dict[str, Any], quantity: int) -> None:
    cart = get_cart()
    if quantity <= 0:
        cart.pop(item["item_id"], None)
    elif item["is_unique"]:
        cart[item["item_id"]] = 1
    else:
        cart[item["item_id"]] = min(quantity, 99)
    session.modified = True


def clear_cart() -> None:
    session["cart"] = {}
    session.modified = True


def cart_count() -> int:
    return sum(get_cart().values())
