from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


def is_tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def normalize_ocr_text(text: str) -> str:
    cleaned = text.replace("\x0c", " ")
    cleaned = re.sub(r"\r\n?", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_text(path: Path) -> str:
    command = ["tesseract", str(path), "stdout", "--psm", "6"]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return normalize_ocr_text(result.stdout)
