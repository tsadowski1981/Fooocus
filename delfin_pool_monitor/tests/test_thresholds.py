from datetime import datetime

from delfin_monitor.config import Thresholds
from delfin_monitor.models import AlarmLevel, SensorReading
from delfin_monitor.thresholds import evaluate

THRESHOLDS = Thresholds(ph_min=7.0, ph_max=7.4, chlorine_min=0.1)


def make_reading(ph=7.2, chlorine=0.3):
    return SensorReading(timestamp=datetime.now(), ph=ph, chlorine=chlorine)


def test_no_alarms_when_within_range():
    alarms = evaluate(make_reading(ph=7.2, chlorine=0.3), THRESHOLDS)
    assert alarms == []


def test_ph_too_low_triggers_alarm():
    alarms = evaluate(make_reading(ph=6.5, chlorine=0.3), THRESHOLDS)
    assert len(alarms) == 1
    assert alarms[0].parameter == "ph"
    assert alarms[0].level == AlarmLevel.ALARM


def test_ph_too_high_triggers_alarm():
    alarms = evaluate(make_reading(ph=7.9, chlorine=0.3), THRESHOLDS)
    assert len(alarms) == 1
    assert alarms[0].parameter == "ph"


def test_ph_at_exact_boundaries_is_ok():
    assert evaluate(make_reading(ph=7.0, chlorine=0.3), THRESHOLDS) == []
    assert evaluate(make_reading(ph=7.4, chlorine=0.3), THRESHOLDS) == []


def test_chlorine_below_minimum_triggers_alarm():
    alarms = evaluate(make_reading(ph=7.2, chlorine=0.05), THRESHOLDS)
    assert len(alarms) == 1
    assert alarms[0].parameter == "chlorine"
    assert alarms[0].level == AlarmLevel.ALARM


def test_both_out_of_range_triggers_two_alarms():
    alarms = evaluate(make_reading(ph=6.0, chlorine=0.0), THRESHOLDS)
    assert {a.parameter for a in alarms} == {"ph", "chlorine"}


def test_missing_values_produce_warning():
    alarms = evaluate(make_reading(ph=None, chlorine=None), THRESHOLDS)
    assert len(alarms) == 2
    assert all(a.level == AlarmLevel.WARNING for a in alarms)
