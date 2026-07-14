"""Command line entry point.

    python -m delfin_monitor report       # fetch + evaluate + notify + save (for cron @ 18:00)
    python -m delfin_monitor discover     # dump raw Tuya DPS status, to configure config.yaml
    python -m delfin_monitor test-alert   # send a test WhatsApp message via CallMeBot
    python -m delfin_monitor tui          # launch the interactive TUI dashboard
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .notifier import send_whatsapp
from .report import run_daily_report
from .sensor_client import get_sensor_client


def _cmd_report(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    result = run_daily_report(config)
    print(result.text)
    if result.alarms and not result.notified and config.whatsapp.enabled:
        print("\nUWAGA: nie udalo sie wyslac alarmu WhatsApp - sprawdz logi.", file=sys.stderr)
        return 1
    return 0


def _cmd_discover(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    client = get_sensor_client(config)

    print("Surowe dane ze statusu (/status) czujnika Delfin:\n")
    status_list = client.raw_status()
    if not status_list:
        print("  (brak)")
    for item in status_list:
        print(f"  code={item.get('code')!r:30} value={item.get('value')!r}")

    logs = client.raw_logs()
    print(f"\nOstatnie wpisy z logow urzadzenia (/logs, ostatnie 48h, {len(logs)} wpisow):\n")
    if not logs:
        print("  (brak - albo urzadzenie nie wspiera tego endpointu, albo brak nowych zdarzen)")
    for entry in logs[:40]:
        print(f"  {entry!r}")

    print(
        "\nPorownaj powyzsze wartosci z tym co pokazuje aplikacja 'Moj dom' i "
        "ustaw wlasciwe 'code' oraz 'scale' w config.yaml (sekcja tuya.dps_mapping). "
        "Jesli parametru brakuje w /status, ale jest w /logs, sprawdz pod jakim polem "
        "(prawdopodobnie 'code') i jaka wartosc (prawdopodobnie 'value') sie tam pojawia."
    )
    return 0


def _cmd_test_alert(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if not config.whatsapp.enabled:
        print(
            "whatsapp.enabled=false w config.yaml - nic nie wyslano. "
            "Ustaw enabled: true, phone i apikey, i sprobuj ponownie.",
            file=sys.stderr,
        )
        return 1
    message = args.message or "Test alarmu z Delfin Pool Monitor - jesli to widzisz, dziala!"
    send_whatsapp(config.whatsapp, message)
    print("Wyslano wiadomosc testowa WhatsApp.")
    return 0


def _cmd_tui(args: argparse.Namespace) -> int:
    from .tui import DelfinApp

    config = load_config(args.config)
    DelfinApp(config).run()
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(prog="delfin_monitor")
    parser.add_argument("--config", default=None, help="Sciezka do config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="Wykonaj raport (przeznaczone dla cron)")
    p_report.set_defaults(func=_cmd_report)

    p_discover = sub.add_parser("discover", help="Pokaz surowe dane DPS z czujnika")
    p_discover.set_defaults(func=_cmd_discover)

    p_test = sub.add_parser("test-alert", help="Wyslij testowy alarm WhatsApp")
    p_test.add_argument("--message", default=None)
    p_test.set_defaults(func=_cmd_test_alert)

    p_tui = sub.add_parser("tui", help="Uruchom interaktywny dashboard TUI")
    p_tui.set_defaults(func=_cmd_tui)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
