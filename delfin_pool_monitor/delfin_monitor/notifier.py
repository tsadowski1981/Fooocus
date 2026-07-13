"""Sends WhatsApp alarm messages via CallMeBot."""
from __future__ import annotations

import logging

import requests

from .config import WhatsAppConfig

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


class NotifierError(Exception):
    pass


def send_whatsapp(config: WhatsAppConfig, message: str) -> None:
    if not config.enabled:
        logger.info("WhatsApp wylaczony w konfiguracji, pomijam wysylke alarmu.")
        return

    if config.provider != "callmebot":
        raise NotifierError(f"Nieobslugiwany dostawca WhatsApp: {config.provider}")

    if not config.phone or not config.apikey:
        raise NotifierError(
            "Brak numeru telefonu lub apikey CallMeBot w config.yaml (whatsapp.phone / "
            "whatsapp.apikey). Zobacz README.md, sekcja 'Alarmy na WhatsApp (CallMeBot)'."
        )

    params = {"phone": config.phone, "text": message, "apikey": config.apikey}
    response = requests.get(CALLMEBOT_URL, params=params, timeout=15)
    response.raise_for_status()
