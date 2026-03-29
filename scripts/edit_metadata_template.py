#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = """- id: {item_id}
  title: {title}
  description: ""
  dimensions: ""
  condition_note: "Skladovy kus, bez zaruky."
  status: available
  is_unique: true
  images:
    - {image_name}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vygeneruje YAML sablonu pro novou katalogovou polozku.")
    parser.add_argument("item_id", help="ID polozky.")
    parser.add_argument("image_name", help="Nazev obrazku v media/originals.")
    parser.add_argument("--title", default="Nova polozka", help="Titulek polozky.")
    parser.add_argument("--output", default=None, help="Volitelny vystupni soubor.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = TEMPLATE.format(item_id=args.item_id, title=args.title, image_name=args.image_name)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Template written to {args.output}")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
