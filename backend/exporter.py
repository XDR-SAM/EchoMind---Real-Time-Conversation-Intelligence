"""Export helpers for EchoMind sessions.

Supported formats:
- json
- csv
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _coerce_records(transcripts: Any, fmt: str) -> list[dict[str, Any]]:
    if not transcripts:
        return []
    first = transcripts[0]
    if isinstance(first, dict):
        return [dict(item) for item in transcripts]
    return [{"text": str(item)} for item in transcripts]


def export_session(path: str | Path, transcripts: Any, fmt: str = "json") -> str:
    fmt = (fmt or "json").lower().strip()
    _ensure_parent(path)
    path = str(path)
    rows = _coerce_records(transcripts, fmt)
    if fmt == "csv":
        fieldnames = sorted({key for row in rows for key in row.keys()})
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return path
