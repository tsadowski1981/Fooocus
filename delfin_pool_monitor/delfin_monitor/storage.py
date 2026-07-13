"""Append-only JSONL history of daily readings/alarms."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Alarm, AlarmLevel, SensorReading


def append_history(path: Path, reading: SensorReading, alarms: list[Alarm]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "reading": reading.to_dict(),
        "alarms": [
            {"level": a.level.value, "parameter": a.parameter, "message": a.message}
            for a in alarms
        ],
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history(path: Path, limit: int = 30) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    return entries[-limit:]
