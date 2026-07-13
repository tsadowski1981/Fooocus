# Delfin Pool Monitor

Codzienny raport (18:00) i alarmy WhatsApp z czujnika basenowego **Delfin**
(widoczny w aplikacji "Moj dom" jako urządzenie Tuya z parametrami pH, CL,
TDS, EC, SALT, ORP, temperatura, bateria).

- Codziennie o 18:00 (przez cron) pobiera odczyt z czujnika, zapisuje go do
  historii i pokazuje raport.
- Jeśli **pH** wyjdzie poza zakres **7.0-7.4** albo **chlor** spadnie poniżej
  **0.1 mg/L** - wysyła alarm na WhatsApp (przez CallMeBot).
- Interaktywny dashboard TUI (`delfin_monitor tui`) do podglądu na żywo i
  historii odczytów.

## 1. Instalacja

```bash
cd delfin_pool_monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
```

`config.yaml` jest w `.gitignore` - zawiera Twoje sekrety (klucze API, numer
telefonu), więc nigdy nie trafi do repozytorium.

## 2. Podłączenie czujnika Delfin (Tuya Cloud API)

Delfin jest urządzeniem Tuya, więc dane pobieramy przez oficjalne API Tuya
(bezpłatne dla użytku prywatnego):

1. Załóż konto na [iot.tuya.com](https://iot.tuya.com) i utwórz **Cloud
   Project** (przy tworzeniu wybierz region centrum danych zgodny z Twoją
   lokalizacją - dla Polski/Europy zwykle "Central Europe" / `eu`).
2. W projekcie wejdź w zakładkę **Devices → Link Tuya App Account → Add App
   Account**, wybierz "Automatic" i "Read Only Status" - pojawi się kod QR.
3. W aplikacji "Moj dom" (lub Smart Life/Tuya Smart, jeśli to ona zarządza
   czujnikiem) wejdź w zakładkę **Ja/Me → ikona QR** w prawym górnym rogu i
   zeskanuj kod. Wszystkie Twoje urządzenia (w tym Delfin) pojawią się w
   projekcie Tuya.
4. W zakładce **Overview** projektu skopiuj **Access ID/Client ID** oraz
   **Access Secret/Client Secret** do `config.yaml` (`tuya.access_id`,
   `tuya.access_secret`).
5. W zakładce **Devices** znajdź urządzenie "Delfin" i skopiuj jego
   **Device ID** do `config.yaml` (`tuya.device_id`).

Następnie sprawdź, jakie dokładnie dane (kody DPS) zwraca Twój egzemplarz:

```bash
python -m delfin_monitor discover
```

Porównaj wypisane wartości z tym, co pokazuje aplikacja "Moj dom" (np. pH
7.0, CL 0.2 mg/L) i w razie potrzeby popraw `tuya.dps_mapping` w
`config.yaml` (nazwę kodu `code` i współczynnik skalowania `scale` - Tuya
często przechowuje liczby dziesiętne jako liczby całkowite, np. pH 7.0 jako
surowe `70`, stąd `scale: 10`).

Zanim skonfigurujesz Tuya, możesz przetestować resztę aplikacji z
przykładowymi danymi ustawiając `tuya.mock: true` w `config.yaml`.

## 3. Alarmy na WhatsApp (CallMeBot)

1. Dodaj do kontaktów numer CallMeBot: **+34 644 59 71 36**.
2. Wyślij do niego na WhatsApp wiadomość: `I allow callmebot to send me messages`.
3. Bot odpowie wiadomością z Twoim osobistym `apikey`.
4. Uzupełnij w `config.yaml`:
   ```yaml
   whatsapp:
     enabled: true
     phone: "+48XXXXXXXXX"   # Twój numer, format międzynarodowy
     apikey: "TWOJ_APIKEY"
   ```
5. Przetestuj:
   ```bash
   python -m delfin_monitor test-alert
   ```

## 4. Codzienny raport o 18:00 (cron)

```bash
bash scripts/install_cron.sh
```

Doda wpis do crontab: `0 18 * * * ... python -m delfin_monitor report`.
Logi trafiają do `data/cron.log`. Żeby usunąć wpis, edytuj `crontab -e`
ręcznie.

Komputer/serwer musi być włączony o 18:00, żeby cron zadziałał - jeśli
uruchamiasz to na laptopie, rozważ Raspberry Pi lub serwerek domowy.

## 5. Interaktywny dashboard (TUI)

```bash
python -m delfin_monitor tui
```

Skróty klawiszowe:
- `r` - pobierz nowy odczyt, zapisz do historii, wyślij alarm jeśli trzeba
- `t` - wyślij testowy alarm WhatsApp
- `q` - wyjście

## Progi alarmowe

Domyślnie w `config.yaml`:

```yaml
thresholds:
  ph_min: 7.0
  ph_max: 7.4
  chlorine_min: 0.1
```

## Struktura projektu

```
delfin_monitor/
  cli.py            # komendy: report / discover / test-alert / tui
  config.py         # wczytywanie config.yaml
  sensor_client.py  # klient Tuya Cloud API (+ tryb mock)
  thresholds.py     # ocena progów pH/chloru
  notifier.py       # alarmy WhatsApp (CallMeBot)
  storage.py        # historia odczytów (data/history.jsonl)
  report.py         # budowanie raportu + orkiestracja
  tui.py            # dashboard Textual
tests/              # pytest - progi, klient, raport
scripts/install_cron.sh
```

## Testy

```bash
pip install pytest
pytest
```
