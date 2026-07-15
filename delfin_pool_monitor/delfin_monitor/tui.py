"""Interactive TUI dashboard (Textual) for the Delfin pool sensor.

Keys: r = pobierz nowy odczyt i wykonaj pelny raport (zapis + powiadomienie)
      t = wyslij testowe powiadomienie
      q = wyjdz
"""
from __future__ import annotations

from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Static

from .config import AppConfig
from .models import AlarmLevel, ReportResult
from .notifier import send_notification
from .report import run_daily_report
from .storage import read_history

STATUS_STYLE = {
    AlarmLevel.OK: "bold white on green",
    AlarmLevel.WARNING: "bold black on yellow",
    AlarmLevel.ALARM: "bold white on red",
}


class DelfinApp(App):
    CSS = """
    #status { height: 3; content-align: center middle; margin: 1 2; }
    #params { height: 12; margin: 0 2; }
    #history { height: 1fr; margin: 0 2 1 2; }
    """

    BINDINGS = [
        ("r", "refresh", "Nowy raport teraz"),
        ("t", "test_alert", "Testowe powiadomienie"),
        ("q", "quit", "Wyjdz"),
    ]

    TITLE = "Delfin - monitor basenu"

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config_obj = config

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Nacisnij [r] aby pobrac pierwszy odczyt z czujnika Delfin.", id="status")
        with Vertical():
            yield DataTable(id="params")
            yield DataTable(id="history")
        yield Footer()

    def on_mount(self) -> None:
        params = self.query_one("#params", DataTable)
        params.add_columns("Parametr", "Wartosc", "Norma")
        params.cursor_type = "row"

        history = self.query_one("#history", DataTable)
        history.add_columns("Data/godzina", "pH", "Chlor (mg/L)", "Status")
        history.cursor_type = "row"

        self._load_history()

    def _load_history(self) -> None:
        history_table = self.query_one("#history", DataTable)
        history_table.clear()
        entries = read_history(self.config_obj.history_path(), limit=30)
        for entry in reversed(entries):
            reading = entry["reading"]
            alarms = entry.get("alarms", [])
            status = "ALARM" if any(a["level"] == "ALARM" for a in alarms) else "OK"
            ts = datetime.fromisoformat(reading["timestamp"]).strftime("%Y-%m-%d %H:%M")
            ph = f"{reading['ph']:.2f}" if reading.get("ph") is not None else "-"
            cl = f"{reading['chlorine']:.2f}" if reading.get("chlorine") is not None else "-"
            history_table.add_row(ts, ph, cl, status)

    def _render_result(self, result: ReportResult) -> None:
        status_widget = self.query_one("#status", Static)
        style = STATUS_STYLE[result.status]
        text = (
            f"Status: {result.status.value}  |  "
            f"Ostatni odczyt: {result.reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            + ("  |  Powiadomienie wyslane" if result.notified else "")
        )
        status_widget.update(f"[{style}]{text}[/]")

        params = self.query_one("#params", DataTable)
        params.clear()
        r = result.reading
        th = self.config_obj.thresholds
        rows = [
            ("pH", r.ph, f"{th.ph_min:.1f} - {th.ph_max:.1f}"),
            ("Chlor (mg/L)", r.chlorine, f">= {th.chlorine_min:.2f}"),
            ("Temperatura (C)", r.temperature, "-"),
            ("TDS (ppm)", r.tds, "-"),
            ("EC (uS/cm)", r.ec, "-"),
            ("Sol (ppm)", r.salt, "-"),
            ("ORP (mV)", r.orp, "-"),
            ("Bateria (%)", r.battery, "-"),
        ]
        for name, value, norm in rows:
            params.add_row(name, "brak danych" if value is None else f"{value}", norm)

        if result.alarms:
            self.notify(
                "\n".join(a.message for a in result.alarms),
                title="Alarm basenu Delfin",
                severity="error",
            )

        self._load_history()

    def action_refresh(self) -> None:
        status_widget = self.query_one("#status", Static)
        status_widget.update("Pobieram odczyt z czujnika Delfin...")
        self.run_worker(self._do_refresh, thread=True, exclusive=True)

    def _do_refresh(self) -> None:
        try:
            result = run_daily_report(self.config_obj)
        except Exception as exc:  # noqa: BLE001 - surface any adapter/network error in the UI
            self.call_from_thread(self._show_error, f"Blad pobierania odczytu: {exc}")
            return
        self.call_from_thread(self._render_result, result)

    def action_test_alert(self) -> None:
        self.run_worker(self._do_test_alert, thread=True, exclusive=True)

    def _do_test_alert(self) -> None:
        try:
            send_notification(
                self.config_obj.notify,
                "Test alarmu z Delfin Pool Monitor - jesli to widzisz, dziala!",
            )
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(self._show_error, f"Blad wysylki powiadomienia: {exc}")
            return
        self.call_from_thread(
            self.notify, "Wyslano testowe powiadomienie.", title="OK"
        )

    def _show_error(self, message: str) -> None:
        self.query_one("#status", Static).update(message)
        self.notify(message, title="Blad", severity="error")
