"""Configuration loading for the Delfin pool monitor."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class DpsField:
    code: str
    scale: float = 1.0


@dataclass
class TuyaConfig:
    api_region: str = "eu"
    access_id: str = ""
    access_secret: str = ""
    device_id: str = ""
    dps_mapping: dict[str, DpsField] = field(default_factory=dict)
    mock: bool = False


@dataclass
class Thresholds:
    ph_min: float = 7.0
    ph_max: float = 7.4
    chlorine_min: float = 0.1


@dataclass
class WhatsAppConfig:
    enabled: bool = False
    provider: str = "callmebot"
    phone: str = ""
    apikey: str = ""


@dataclass
class ReportConfig:
    time: str = "18:00"
    timezone: str = "Europe/Warsaw"


@dataclass
class StorageConfig:
    history_file: str = "data/history.jsonl"


@dataclass
class AppConfig:
    tuya: TuyaConfig = field(default_factory=TuyaConfig)
    thresholds: Thresholds = field(default_factory=Thresholds)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    base_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG_PATH.parent)

    def history_path(self) -> Path:
        p = Path(self.storage.history_file)
        return p if p.is_absolute() else self.base_dir / p


_DEFAULT_DPS_MAPPING = {
    "ph": {"code": "ph_value", "scale": 10},
    "chlorine": {"code": "cl_value", "scale": 100},
    "temperature": {"code": "temp_current", "scale": 10},
    "tds": {"code": "tds_value", "scale": 1},
    "ec": {"code": "ec_value", "scale": 1},
    "salt": {"code": "salt_value", "scale": 1},
    "orp": {"code": "orp_value", "scale": 1},
    "battery": {"code": "battery_percentage", "scale": 1},
}


def _env_override(value: str, env_var: str) -> str:
    return os.environ.get(env_var, value)


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load config.yaml (falling back to defaults for anything missing).

    Secrets can also be supplied via environment variables, which take
    precedence over the file: DELFIN_TUYA_ACCESS_ID, DELFIN_TUYA_ACCESS_SECRET,
    DELFIN_TUYA_DEVICE_ID, DELFIN_CALLMEBOT_PHONE, DELFIN_CALLMEBOT_APIKEY.
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    tuya_data = data.get("tuya", {}) or {}
    mapping_data = tuya_data.get("dps_mapping") or _DEFAULT_DPS_MAPPING
    dps_mapping = {
        name: DpsField(code=v["code"], scale=float(v.get("scale", 1)))
        for name, v in mapping_data.items()
    }
    tuya = TuyaConfig(
        api_region=tuya_data.get("api_region", "eu"),
        access_id=_env_override(tuya_data.get("access_id", ""), "DELFIN_TUYA_ACCESS_ID"),
        access_secret=_env_override(
            tuya_data.get("access_secret", ""), "DELFIN_TUYA_ACCESS_SECRET"
        ),
        device_id=_env_override(tuya_data.get("device_id", ""), "DELFIN_TUYA_DEVICE_ID"),
        dps_mapping=dps_mapping,
        mock=bool(tuya_data.get("mock", False)),
    )

    th_data = data.get("thresholds", {}) or {}
    thresholds = Thresholds(
        ph_min=float(th_data.get("ph_min", 7.0)),
        ph_max=float(th_data.get("ph_max", 7.4)),
        chlorine_min=float(th_data.get("chlorine_min", 0.1)),
    )

    wa_data = data.get("whatsapp", {}) or {}
    whatsapp = WhatsAppConfig(
        enabled=bool(wa_data.get("enabled", False)),
        provider=wa_data.get("provider", "callmebot"),
        phone=_env_override(wa_data.get("phone", ""), "DELFIN_CALLMEBOT_PHONE"),
        apikey=_env_override(wa_data.get("apikey", ""), "DELFIN_CALLMEBOT_APIKEY"),
    )

    rep_data = data.get("report", {}) or {}
    report = ReportConfig(
        time=rep_data.get("time", "18:00"),
        timezone=rep_data.get("timezone", "Europe/Warsaw"),
    )

    st_data = data.get("storage", {}) or {}
    storage = StorageConfig(history_file=st_data.get("history_file", "data/history.jsonl"))

    return AppConfig(
        tuya=tuya,
        thresholds=thresholds,
        whatsapp=whatsapp,
        report=report,
        storage=storage,
        base_dir=cfg_path.parent,
    )
