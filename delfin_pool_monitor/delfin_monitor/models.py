"""Data models shared across the app."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class SensorReading:
    """A single snapshot of pool water parameters read from the Delfin sensor."""

    timestamp: datetime
    ph: float | None = None
    chlorine: float | None = None
    temperature: float | None = None
    tds: float | None = None
    ec: float | None = None
    salt: float | None = None
    orp: float | None = None
    battery: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "ph": self.ph,
            "chlorine": self.chlorine,
            "temperature": self.temperature,
            "tds": self.tds,
            "ec": self.ec,
            "salt": self.salt,
            "orp": self.orp,
            "battery": self.battery,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SensorReading":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ph=data.get("ph"),
            chlorine=data.get("chlorine"),
            temperature=data.get("temperature"),
            tds=data.get("tds"),
            ec=data.get("ec"),
            salt=data.get("salt"),
            orp=data.get("orp"),
            battery=data.get("battery"),
        )


class AlarmLevel(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    ALARM = "ALARM"


@dataclass
class Alarm:
    level: AlarmLevel
    parameter: str
    message: str


@dataclass
class ReportResult:
    reading: SensorReading
    alarms: list[Alarm]
    text: str
    notified: bool = False
    pump_activated: bool = False

    @property
    def status(self) -> AlarmLevel:
        if any(a.level == AlarmLevel.ALARM for a in self.alarms):
            return AlarmLevel.ALARM
        if any(a.level == AlarmLevel.WARNING for a in self.alarms):
            return AlarmLevel.WARNING
        return AlarmLevel.OK
