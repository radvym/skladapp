from __future__ import annotations

import re
from typing import Any


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^[0-9+() /-]{7,20}$")


def validate_checkout_form(form: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    cleaned = {
        "first_name": (form.get("first_name") or "").strip(),
        "last_name": (form.get("last_name") or "").strip(),
        "city": (form.get("city") or "").strip(),
        "email": (form.get("email") or "").strip(),
        "phone": (form.get("phone") or "").strip(),
        "note": (form.get("note") or "").strip(),
        "website": (form.get("website") or "").strip(),
        "started_at": (form.get("started_at") or "").strip(),
    }
    errors: dict[str, str] = {}

    for field in ["first_name", "last_name", "city", "email", "phone"]:
        if not cleaned[field]:
            errors[field] = "Toto pole je povinné."

    if cleaned["email"] and not EMAIL_RE.match(cleaned["email"]):
        errors["email"] = "Zadejte platný e-mail."

    if cleaned["phone"] and not PHONE_RE.match(cleaned["phone"]):
        errors["phone"] = "Zadejte platné telefonní číslo."

    if cleaned["website"]:
        errors["website"] = "Formulář se nepodařilo ověřit."

    return cleaned, errors
