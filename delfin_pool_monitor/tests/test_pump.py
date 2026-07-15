from datetime import datetime

from delfin_monitor.config import AppConfig, PumpConfig
from delfin_monitor.models import SensorReading
from delfin_monitor.pump import maybe_run_chlorine_pump


def make_config(**pump_kwargs):
    defaults = dict(
        enabled=True,
        device_id="pump123",
        switch_code="switch_1",
        countdown_code="countdown_1",
        run_seconds=300,
        on_below=0.09,
    )
    defaults.update(pump_kwargs)
    config = AppConfig()
    config.pump = PumpConfig(**defaults)
    return config


def make_reading(chlorine):
    return SensorReading(timestamp=datetime.now(), chlorine=chlorine)


def test_pump_not_triggered_when_disabled(monkeypatch):
    config = make_config(enabled=False)
    calls = []
    monkeypatch.setattr(
        "delfin_monitor.pump.TuyaCloudClient.send_command",
        lambda self, device_id, commands: calls.append((device_id, commands)),
    )

    activated = maybe_run_chlorine_pump(config, make_reading(0.05))

    assert activated is False
    assert calls == []


def test_pump_not_triggered_above_threshold(monkeypatch):
    config = make_config()
    calls = []
    monkeypatch.setattr(
        "delfin_monitor.pump.TuyaCloudClient.send_command",
        lambda self, device_id, commands: calls.append((device_id, commands)),
    )

    activated = maybe_run_chlorine_pump(config, make_reading(0.2))

    assert activated is False
    assert calls == []


def test_pump_triggered_below_threshold(monkeypatch):
    config = make_config()
    calls = []
    monkeypatch.setattr(
        "delfin_monitor.pump.TuyaCloudClient.send_command",
        lambda self, device_id, commands: calls.append((device_id, commands)),
    )

    activated = maybe_run_chlorine_pump(config, make_reading(0.05))

    assert activated is True
    assert len(calls) == 1
    device_id, commands = calls[0]
    assert device_id == "pump123"
    assert {"code": "switch_1", "value": True} in commands
    assert {"code": "countdown_1", "value": 300} in commands


def test_pump_skipped_when_no_device_id(monkeypatch):
    config = make_config(device_id="")
    calls = []
    monkeypatch.setattr(
        "delfin_monitor.pump.TuyaCloudClient.send_command",
        lambda self, device_id, commands: calls.append((device_id, commands)),
    )

    activated = maybe_run_chlorine_pump(config, make_reading(0.05))

    assert activated is False
    assert calls == []


def test_pump_not_triggered_when_chlorine_missing(monkeypatch):
    config = make_config()
    calls = []
    monkeypatch.setattr(
        "delfin_monitor.pump.TuyaCloudClient.send_command",
        lambda self, device_id, commands: calls.append((device_id, commands)),
    )

    activated = maybe_run_chlorine_pump(config, make_reading(None))

    assert activated is False
    assert calls == []
