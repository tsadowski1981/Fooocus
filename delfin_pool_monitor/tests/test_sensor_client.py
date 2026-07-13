from delfin_monitor.config import AppConfig, DpsField, TuyaConfig
from delfin_monitor.sensor_client import MockDelfinClient, TuyaDelfinClient


def make_config():
    tuya = TuyaConfig(
        api_region="eu",
        access_id="id",
        access_secret="secret",
        device_id="dev123",
        dps_mapping={
            "ph": DpsField(code="ph_value", scale=10),
            "chlorine": DpsField(code="cl_value", scale=100),
            "temperature": DpsField(code="temp_current", scale=10),
        },
    )
    return AppConfig(tuya=tuya)


def test_tuya_client_applies_scale_to_raw_dps_values(monkeypatch):
    config = make_config()
    client = TuyaDelfinClient(config)
    monkeypatch.setattr(
        client,
        "raw_status",
        lambda: [
            {"code": "ph_value", "value": 72},
            {"code": "cl_value", "value": 20},
            {"code": "temp_current", "value": 268},
        ],
    )

    reading = client.fetch_reading()

    assert reading.ph == 7.2
    assert reading.chlorine == 0.2
    assert reading.temperature == 26.8


def test_tuya_client_missing_dps_code_yields_none(monkeypatch):
    config = make_config()
    client = TuyaDelfinClient(config)
    monkeypatch.setattr(client, "raw_status", lambda: [{"code": "ph_value", "value": 70}])

    reading = client.fetch_reading()

    assert reading.ph == 7.0
    assert reading.chlorine is None


def test_mock_client_returns_plausible_reading():
    reading = MockDelfinClient(seed=1).fetch_reading()

    assert 6.0 <= reading.ph <= 8.5
    assert reading.chlorine is not None
