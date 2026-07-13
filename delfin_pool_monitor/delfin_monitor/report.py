"""Builds the daily report text and orchestrates fetch -> evaluate -> notify -> store."""
from __future__ import annotations

import logging

from .config import AppConfig
from .models import Alarm, AlarmLevel, ReportResult, SensorReading
from .notifier import send_whatsapp
from .sensor_client import get_sensor_client
from .storage import append_history
from .thresholds import evaluate

logger = logging.getLogger(__name__)


def _fmt(value: float | None, unit: str, decimals: int = 2) -> str:
    if value is None:
        return "brak danych"
    return f"{value:.{decimals}f} {unit}"


def build_report_text(reading: SensorReading, alarms: list[Alarm], config: AppConfig) -> str:
    status = "ALARM" if any(a.level == AlarmLevel.ALARM for a in alarms) else "OK"
    lines = [
        f"Raport basenu Delfin - {reading.timestamp.strftime('%Y-%m-%d %H:%M')}",
        f"Status: {status}",
        "",
        f"pH:      {_fmt(reading.ph, '', 2)} (norma "
        f"{config.thresholds.ph_min:.1f}-{config.thresholds.ph_max:.1f})",
        f"Chlor:   {_fmt(reading.chlorine, 'mg/L', 2)} "
        f"(min {config.thresholds.chlorine_min:.2f} mg/L)",
        f"Temp.:   {_fmt(reading.temperature, 'C', 1)}",
        f"TDS:     {_fmt(reading.tds, 'ppm', 0)}",
        f"EC:      {_fmt(reading.ec, 'uS/cm', 0)}",
        f"Sol:     {_fmt(reading.salt, 'ppm', 0)}",
        f"ORP:     {_fmt(reading.orp, 'mV', 0)}",
        f"Bateria: {_fmt(reading.battery, '%', 0)}",
    ]
    if alarms:
        lines.append("")
        lines.append("Alarmy:")
        for alarm in alarms:
            lines.append(f"  [{alarm.level.value}] {alarm.message}")
    return "\n".join(lines)


def run_daily_report(config: AppConfig) -> ReportResult:
    client = get_sensor_client(config)
    reading = client.fetch_reading()
    alarms = evaluate(reading, config.thresholds)
    text = build_report_text(reading, alarms, config)

    append_history(config.history_path(), reading, alarms)

    notified = False
    if any(a.level == AlarmLevel.ALARM for a in alarms):
        try:
            send_whatsapp(config.whatsapp, text)
            notified = True
        except Exception:
            logger.exception("Nie udalo sie wyslac alarmu WhatsApp")

    return ReportResult(reading=reading, alarms=alarms, text=text, notified=notified)
