"""Turns on the "Pompka chlor" Tuya smart plug when chlorine is critically low."""
from __future__ import annotations

import logging

from .config import AppConfig
from .models import SensorReading
from .tuya_api import TuyaCloudClient

logger = logging.getLogger(__name__)


def maybe_run_chlorine_pump(config: AppConfig, reading: SensorReading) -> bool:
    """Returns True if the pump was switched on."""
    pump = config.pump
    if not pump.enabled:
        return False
    if reading.chlorine is None or reading.chlorine >= pump.on_below:
        return False
    if not pump.device_id:
        logger.warning("pump.enabled=true, ale brak pump.device_id w config.yaml - pomijam.")
        return False

    commands = [{"code": pump.switch_code, "value": True}]
    if pump.countdown_code:
        commands.append({"code": pump.countdown_code, "value": pump.run_seconds})

    client = TuyaCloudClient(
        api_region=config.tuya.api_region,
        access_id=config.tuya.access_id,
        access_secret=config.tuya.access_secret,
    )
    client.send_command(pump.device_id, commands)
    logger.info(
        "Chlor = %.2f mg/L < %.2f - uruchomiono pompke chloru (%s, %ss).",
        reading.chlorine,
        pump.on_below,
        pump.device_id,
        pump.run_seconds,
    )
    return True
