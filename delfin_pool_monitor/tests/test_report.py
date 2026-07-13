from datetime import datetime

from delfin_monitor.config import AppConfig
from delfin_monitor.models import SensorReading
from delfin_monitor.thresholds import evaluate
from delfin_monitor.report import build_report_text


def test_report_text_flags_alarm_status():
    config = AppConfig()
    reading = SensorReading(timestamp=datetime(2026, 7, 13, 18, 0), ph=6.5, chlorine=0.05)
    alarms = evaluate(reading, config.thresholds)

    text = build_report_text(reading, alarms, config)

    assert "ALARM" in text
    assert "pH" in text
    assert "Chlor" in text


def test_report_text_ok_status_when_within_range():
    config = AppConfig()
    reading = SensorReading(timestamp=datetime(2026, 7, 13, 18, 0), ph=7.2, chlorine=0.3)
    alarms = evaluate(reading, config.thresholds)

    text = build_report_text(reading, alarms, config)

    assert "Status: OK" in text
