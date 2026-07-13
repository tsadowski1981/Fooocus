"""Threshold evaluation for pool water parameters."""
from __future__ import annotations

from .config import Thresholds
from .models import Alarm, AlarmLevel, SensorReading


def evaluate(reading: SensorReading, thresholds: Thresholds) -> list[Alarm]:
    alarms: list[Alarm] = []

    if reading.ph is None:
        alarms.append(
            Alarm(AlarmLevel.WARNING, "ph", "Brak odczytu pH z czujnika Delfin.")
        )
    elif not (thresholds.ph_min <= reading.ph <= thresholds.ph_max):
        alarms.append(
            Alarm(
                AlarmLevel.ALARM,
                "ph",
                f"pH = {reading.ph:.2f} poza zakresem "
                f"{thresholds.ph_min:.1f}-{thresholds.ph_max:.1f}!",
            )
        )

    if reading.chlorine is None:
        alarms.append(
            Alarm(AlarmLevel.WARNING, "chlorine", "Brak odczytu chloru z czujnika Delfin.")
        )
    elif reading.chlorine < thresholds.chlorine_min:
        alarms.append(
            Alarm(
                AlarmLevel.ALARM,
                "chlorine",
                f"Chlor = {reading.chlorine:.2f} mg/L, poniżej minimum "
                f"{thresholds.chlorine_min:.2f} mg/L!",
            )
        )

    return alarms
