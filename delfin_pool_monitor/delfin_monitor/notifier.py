"""Sends alarm notifications via ntfy.sh (default) or WhatsApp/CallMeBot."""
from __future__ import annotations

import logging

import requests

from .config import NotifyConfig

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
NTFY_URL = "https://ntfy.sh"


class NotifierError(Exception):
    pass


def _send_ntfy(config: NotifyConfig, message: str) -> None:
    if not config.ntfy_topic:
        raise NotifierError(
            "Brak 'ntfy_topic' w config.yaml (notify.ntfy_topic). Zobacz README.md, "
            "sekcja 'Alarmy przez ntfy.sh'."
        )
    response = requests.post(
        f"{NTFY_URL}/{config.ntfy_topic}",
        data=message.encode("utf-8"),
        headers={"Title": "Delfin - alarm basenu"},
        timeout=15,
    )
    response.raise_for_status()


def _send_callmebot(config: NotifyConfig, message: str) -> None:
    if not config.phone or not config.apikey:
        raise NotifierError(
            "Brak numeru telefonu lub apikey CallMeBot w config.yaml (notify.phone / "
            "notify.apikey). Zobacz README.md, sekcja 'Alarmy na WhatsApp (CallMeBot)'."
        )
    params = {"phone": config.phone, "text": message, "apikey": config.apikey}
    response = requests.get(CALLMEBOT_URL, params=params, timeout=15)
    response.raise_for_status()


def send_notification(config: NotifyConfig, message: str) -> None:
    if not config.enabled:
        logger.info("Powiadomienia wylaczone w konfiguracji, pomijam wysylke alarmu.")
        return

    if config.provider == "ntfy":
        _send_ntfy(config, message)
    elif config.provider == "callmebot":
        _send_callmebot(config, message)
    else:
        raise NotifierError(f"Nieobslugiwany dostawca powiadomien: {config.provider}")


# Backwards-compatible alias.
send_whatsapp = send_notification
