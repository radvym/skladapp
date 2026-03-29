from __future__ import annotations

import re
from typing import Any


TRIPLE_PATTERN = re.compile(
    r"(?P<raw>(?P<width>\d+(?:[.,]\d+)?)\s*[x×]\s*(?P<height>\d+(?:[.,]\d+)?)\s*[x×]\s*(?P<depth>\d+(?:[.,]\d+)?)\s*(?P<unit>mm|cm|m)\b)",
    re.IGNORECASE,
)
DOUBLE_PATTERN = re.compile(
    r"(?P<raw>(?P<width>\d+(?:[.,]\d+)?)\s*[x×]\s*(?P<height>\d+(?:[.,]\d+)?)\s*(?P<unit>mm|cm|m)\b)",
    re.IGNORECASE,
)
SINGLE_PATTERN = re.compile(
    r"(?P<raw>(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>mm|cm|m)\b)",
    re.IGNORECASE,
)


def _to_number(value: str) -> float | int:
    normalized = value.replace(",", ".")
    number = float(normalized)
    return int(number) if number.is_integer() else number


def parse_dimensions(text: str) -> dict[str, Any]:
    if not text:
        return {
            "dimensions_raw": "",
            "width": "",
            "height": "",
            "depth": "",
            "dimension_unit": "",
        }

    for pattern in (TRIPLE_PATTERN, DOUBLE_PATTERN, SINGLE_PATTERN):
        match = pattern.search(text)
        if not match:
            continue

        groups = match.groupdict()
        parsed = {
            "dimensions_raw": groups["raw"],
            "width": "",
            "height": "",
            "depth": "",
            "dimension_unit": groups["unit"].lower(),
        }

        if groups.get("width"):
            parsed["width"] = _to_number(groups["width"])
        if groups.get("height"):
            parsed["height"] = _to_number(groups["height"])
        if groups.get("depth"):
            parsed["depth"] = _to_number(groups["depth"])
        if groups.get("value"):
            parsed["width"] = _to_number(groups["value"])

        return parsed

    return {
        "dimensions_raw": "",
        "width": "",
        "height": "",
        "depth": "",
        "dimension_unit": "",
    }
