"""Command line entry point.

    python -m delfin_monitor report       # fetch + evaluate + notify + save (for cron @ 18:00)
    python -m delfin_monitor discover     # dump raw Tuya DPS status, to configure config.yaml
    python -m delfin_monitor discover --device-id <id>  # inspect any other Tuya device (e.g. the pump)
    python -m delfin_monitor test-alert   # send a test notification (ntfy.sh / WhatsApp)
    python -m delfin_monitor pump-test    # manually trigger the chlorine pump, to verify config
    python -m delfin_monitor tui          # launch the interactive TUI dashboard
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from .config import load_config
from .notifier import send_notification
from .report import run_daily_report
from .sensor_client import get_sensor_client
from .tuya_api import TuyaCloudClient


def _cmd_report(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    result = run_daily_report(config)
    print(result.text)
    if result.alarms and not result.notified and config.notify.enabled:
        print("\nUWAGA: nie udalo sie wyslac alarmu - sprawdz logi.", file=sys.stderr)
        return 1
    return 0


def _cmd_discover(args: argparse.Namespace) -> int:
    config = load_config(args.config)

    if args.device_id:
        # Inspect an arbitrary device (e.g. the chlorine pump) using the same
        # Tuya project credentials, instead of the configured Delfin sensor.
        raw_client = TuyaCloudClient(
            api_region=config.tuya.api_region,
            access_id=config.tuya.access_id,
            access_secret=config.tuya.access_secret,
        )
        device_id = args.device_id

        class _Adapter:
            def raw_status(self):
                return raw_client.get_device_status(device_id)

            def raw_logs(self):
                import time as _time

                now_ms = int(_time.time() * 1000)
                return raw_client.get_device_report_logs(device_id, now_ms - 48 * 3600 * 1000, now_ms)

        client = _Adapter()
    else:
        client = get_sensor_client(config)

    print(f"Surowe dane ze statusu (/status) urzadzenia {args.device_id or config.tuya.device_id}:\n")
    status_list = client.raw_status()
    if not status_list:
        print("  (brak)")
    for item in status_list:
        print(f"  code={item.get('code')!r:30} value={item.get('value')!r}")

    logs = client.raw_logs()
    print(f"\nPobrano {len(logs)} wpisow z logow urzadzenia (/logs, ostatnie 48h).")
    if not logs:
        print("  (brak - albo urzadzenie nie wspiera tego endpointu, albo brak nowych zdarzen)")

    codes_seen: dict[str, dict[str, Any]] = {}
    for entry in logs:
        code = entry.get("code")
        if code and code not in codes_seen:
            codes_seen[code] = entry

    print(f"\nUnikalne kody widoczne w calej paczce {len(logs)} wpisow ({len(codes_seen)} kodow):\n")
    for code, entry in sorted(codes_seen.items()):
        print(f"  code={code!r:30} przykladowa wartosc={entry.get('value')!r}")

    print("\nOstatnie (do 40) surowe wpisy /logs:\n")
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
    if not config.notify.enabled:
        print(
            "notify.enabled=false w config.yaml - nic nie wyslano. "
            "Ustaw enabled: true i uzupelnij dane dostawcy, i sprobuj ponownie.",
            file=sys.stderr,
        )
        return 1
    message = args.message or "Test alarmu z Delfin Pool Monitor - jesli to widzisz, dziala!"
    send_notification(config.notify, message)
    print("Wyslano powiadomienie testowe.")
    return 0


def _cmd_tui(args: argparse.Namespace) -> int:
    from .tui import DelfinApp

    config = load_config(args.config)
    DelfinApp(config).run()
    return 0


def _cmd_pump_test(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if not config.pump.device_id:
        print("Brak pump.device_id w config.yaml.", file=sys.stderr)
        return 1

    client = TuyaCloudClient(
        api_region=config.tuya.api_region,
        access_id=config.tuya.access_id,
        access_secret=config.tuya.access_secret,
    )
    commands = [{"code": config.pump.switch_code, "value": True}]
    if config.pump.countdown_code:
        commands.append({"code": config.pump.countdown_code, "value": config.pump.run_seconds})
    client.send_command(config.pump.device_id, commands)
    print(f"Wyslano do pompki ({config.pump.device_id}): {commands}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(prog="delfin_monitor")
    parser.add_argument("--config", default=None, help="Sciezka do config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="Wykonaj raport (przeznaczone dla cron)")
    p_report.set_defaults(func=_cmd_report)

    p_discover = sub.add_parser("discover", help="Pokaz surowe dane DPS z czujnika")
    p_discover.add_argument(
        "--device-id",
        default=None,
        help="Sprawdz inne urzadzenie Tuya (np. pompke chloru) zamiast czujnika Delfin",
    )
    p_discover.set_defaults(func=_cmd_discover)

    p_test = sub.add_parser("test-alert", help="Wyslij testowe powiadomienie")
    p_test.add_argument("--message", default=None)
    p_test.set_defaults(func=_cmd_test_alert)

    p_tui = sub.add_parser("tui", help="Uruchom interaktywny dashboard TUI")
    p_tui.set_defaults(func=_cmd_tui)

    p_pump = sub.add_parser("pump-test", help="Recznie uruchom pompke chloru (test)")
    p_pump.set_defaults(func=_cmd_pump_test)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
