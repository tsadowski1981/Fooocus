"""Clients that turn a Tuya "Delfin" pool sensor into a SensorReading.

The Delfin device (as seen in the "Moj dom" app) is a Tuya sub-device that
reports pH, free chlorine (CL), temperature, TDS, EC, salt and ORP as Tuya
"data points" (DPS). Tuya stores decimals as scaled integers (e.g. a pH of
7.0 is often reported as the raw value 70), so every field in dps_mapping
carries a `scale` divisor alongside the raw DPS `code`.

The exact DPS codes/scales differ per product template, so `discover()`
(exposed via `python -m delfin_monitor discover`) dumps the raw status list
returned by Tuya so you can confirm/adjust config.yaml for your specific unit.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

from .config import AppConfig
from .models import SensorReading
from .tuya_api import TuyaCloudClient

FIELD_NAMES = ["ph", "chlorine", "temperature", "tds", "ec", "salt", "orp", "battery"]


class SensorClient(ABC):
    @abstractmethod
    def fetch_reading(self) -> SensorReading:
        ...

    def raw_status(self) -> list[dict[str, Any]]:
        """Return the raw status payload, for the `discover` command."""
        raise NotImplementedError

    def raw_logs(self) -> list[dict[str, Any]]:
        """Return recent raw data-point report log entries, if supported."""
        return []


class TuyaDelfinClient(SensorClient):
    """Fetches the Delfin device's status via the Tuya Cloud API."""

    def __init__(self, config: AppConfig):
        self._config = config
        self._client: TuyaCloudClient | None = None

    def _get_client(self) -> TuyaCloudClient:
        if self._client is None:
            tuya = self._config.tuya
            if not (tuya.access_id and tuya.access_secret and tuya.device_id):
                raise RuntimeError(
                    "Brak danych logowania Tuya w config.yaml (access_id / "
                    "access_secret / device_id). Zobacz README.md, sekcja "
                    "'Podłączenie czujnika Delfin (Tuya)'."
                )
            self._client = TuyaCloudClient(
                api_region=tuya.api_region,
                access_id=tuya.access_id,
                access_secret=tuya.access_secret,
            )
        return self._client

    def raw_status(self) -> list[dict[str, Any]]:
        client = self._get_client()
        return client.get_device_status(self._config.tuya.device_id)

    def raw_logs(self) -> list[dict[str, Any]]:
        client = self._get_client()
        now = datetime.now()
        start = now - timedelta(hours=48)
        return client.get_device_report_logs(
            self._config.tuya.device_id,
            start_time_ms=int(start.timestamp() * 1000),
            end_time_ms=int(now.timestamp() * 1000),
        )

    def _combined_status(self) -> dict[str, Any]:
        """Live /status values, filled in with the latest /logs value for any
        code that /status doesn't currently report (some sensors on this
        device only ever show up in the report log, not the status cache)."""
        status_by_code = {item["code"]: item["value"] for item in self.raw_status()}
        try:
            logs = self.raw_logs()
        except Exception:
            logs = []
        for entry in logs:
            code = entry.get("code")
            if not code or code in status_by_code:
                continue
            status_by_code[code] = entry.get("value")
        return status_by_code

    def fetch_reading(self) -> SensorReading:
        status_by_code = self._combined_status()

        values: dict[str, float | None] = {}
        for name in FIELD_NAMES:
            dps = self._config.tuya.dps_mapping.get(name)
            if dps is None or dps.code not in status_by_code:
                values[name] = None
                continue
            raw_value = status_by_code[dps.code]
            try:
                values[name] = float(raw_value) / dps.scale if dps.scale else float(raw_value)
            except (TypeError, ValueError):
                values[name] = None

        return SensorReading(timestamp=datetime.now(), raw=status_by_code, **values)


class MockDelfinClient(SensorClient):
    """Generates plausible-looking readings, useful before Tuya is configured."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def raw_status(self) -> list[dict[str, Any]]:
        return [{"code": "mock", "value": "mock-mode-no-raw-data"}]

    def fetch_reading(self) -> SensorReading:
        return SensorReading(
            timestamp=datetime.now(),
            ph=round(self._rng.uniform(6.8, 7.6), 2),
            chlorine=round(self._rng.uniform(0.0, 0.6), 2),
            temperature=round(self._rng.uniform(24.0, 29.0), 1),
            tds=round(self._rng.uniform(300, 600)),
            ec=round(self._rng.uniform(600, 1000)),
            salt=round(self._rng.uniform(300, 600)),
            orp=round(self._rng.uniform(400, 650)),
            battery=round(self._rng.uniform(20, 100)),
            raw={},
        )


def get_sensor_client(config: AppConfig) -> SensorClient:
    if config.tuya.mock:
        return MockDelfinClient()
    return TuyaDelfinClient(config)
