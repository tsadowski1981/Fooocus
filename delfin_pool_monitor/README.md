# Delfin Pool Monitor

Codzienny raport (18:00) i alarmy push z czujnika basenowego **Delfin**
(widoczny w aplikacji "Moj dom" jako urządzenie Tuya z parametrami pH, CL,
TDS, EC, ORP, temperatura, bateria).

- Codziennie o 18:00 (przez cron) pobiera odczyt z czujnika, zapisuje go do
  historii i pokazuje raport.
- Jeśli **pH** wyjdzie poza zakres **7.0-7.4** albo **chlor** spadnie poniżej
  **0.1 mg/L** - wysyła alarm push (przez [ntfy.sh](https://ntfy.sh), albo
  opcjonalnie na WhatsApp przez CallMeBot).
- Interaktywny dashboard TUI (`delfin_monitor tui`) do podglądu na żywo i
  historii odczytów.
- Opcjonalnie: gdy chlor spadnie poniżej **0.09 mg/L**, automatycznie
  włącza inteligentne gniazdko Tuya sterujące pompką dozującą chlor.

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
6. **Kluczowy krok**: domyślnie projekt Tuya udostępnia przez Cloud API
   tylko okrojony, "ujednolicony" zestaw parametrów (u nas: tylko
   temperatura/TDS/bateria - bez pH i chloru!). Żeby zobaczyć wszystkie
   surowe DP-sy urządzenia, wejdź w **Devices → (wiersz "Delfin") → Debug
   Device → zakładka "Device Debugging"**, znajdź link obok napisu
   "Control Device with Standard" (otwiera stronę "Configure Control
   Instruction Mode"), wybierz kartę **"DP Instruction"** zamiast
   "Standard Instruction" i zapisz. Bez tego kroku `discover` pokaże tylko
   niepełny zestaw danych.

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

## 3. Alarmy push (ntfy.sh)

Najprostsza opcja - bez zakładania konta, bez numeru telefonu:

1. Zainstaluj apkę **ntfy** na telefonie ([F-Droid](https://f-droid.org/packages/io.heckel.ntfy/)
   albo Google Play).
2. Wymyśl unikalną, trudną do odgadnięcia nazwę "kanału" (np.
   `delfin-basen-tsadowski-9f31`) - to jak hasło, kto zna nazwę, może czytać
   Twoje powiadomienia, więc niech nie będzie oczywista.
3. W apce ntfy kliknij **"+"** i subskrybuj dokładnie tę nazwę.
4. Uzupełnij w `config.yaml`:
   ```yaml
   notify:
     enabled: true
     provider: ntfy
     ntfy_topic: "delfin-basen-tsadowski-9f31"
   ```
5. Przetestuj:
   ```bash
   python -m delfin_monitor test-alert
   ```
   Powiadomienie powinno przyjść na telefon w kilka sekund.

### Alternatywa: WhatsApp (CallMeBot)

Jeśli wolisz alarm na WhatsApp zamiast osobnej apki:

1. Dodaj do kontaktów numer CallMeBot: **+34 644 59 71 36** (w Kontaktach, nie
   w WhatsAppie).
2. Otwórz **WhatsApp** (nie SMS!) i wyszukaj ten kontakt tam, wewnątrz apki.
3. Wyślij mu wiadomość: `I allow callmebot to send me messages` - upewnij się,
   że pole wpisywania pokazuje "Wiadomość", a nie "SMS".
4. Bot odpowie wiadomością z Twoim osobistym `apikey`.
5. Uzupełnij w `config.yaml`:
   ```yaml
   notify:
     enabled: true
     provider: callmebot
     phone: "+48XXXXXXXXX"   # Twój numer, format międzynarodowy
     apikey: "TWOJ_APIKEY"
   ```
6. Przetestuj: `python -m delfin_monitor test-alert`

## 3b. Automatyczna pompka chloru (opcjonalne)

Jeśli masz osobne inteligentne gniazdko Tuya sterujące pompką dozującą
chlor (np. nazwane "Pompka chlor" w apce "Moj dom"), aplikacja może je
**włączyć automatycznie**, gdy chlor spadnie poniżej krytycznego poziomu
(domyślnie **0.09 mg/L** - niżej niż zwykły alarm na 0.1, więc najpierw
dostajesz powiadomienie, a dopiero przy dalszym spadku pompka rusza sama).

1. W [iot.tuya.com](https://iot.tuya.com), w tej samej zakładce **Devices**,
   znajdź na liście gniazdko (np. "Pompka chlor") i skopiuj jego **Device ID**.
2. Sprawdź jego kody DP (nazwa przełącznika, opcjonalny timer):
   ```bash
   python -m delfin_monitor discover --device-id <DEVICE_ID_POMPKI>
   ```
   Dla zwykłych gniazdek Tuya to zwykle `switch_1` (włącz/wyłącz) i
   `countdown_1` (wbudowany timer w sekundach, jeśli apka pokazuje ikonę
   "Timer" przy tym urządzeniu).
3. Uzupełnij w `config.yaml`:
   ```yaml
   pump:
     enabled: true
     device_id: "DEVICE_ID_POMPKI"
     switch_code: "switch_1"
     countdown_code: "countdown_1"   # "" jesli urzadzenie nie ma timera
     run_seconds: 300                 # ile sekund ma pracowac pompka
     on_below: 0.09
   ```
4. Przetestuj **ręcznie** (bez czekania, aż chlor faktycznie spadnie):
   ```bash
   python -m delfin_monitor pump-test
   ```
   Sprawdź w apce "Moj dom", czy gniazdko się włączyło (i wyłączyło po
   `run_seconds`, jeśli ustawiony jest `countdown_code`).

**Uwaga bezpieczeństwa**: to steruje prawdziwym dozowaniem chemii do
basenu. `run_seconds` powinno być na tyle krótkie, żeby pojedyncze
uruchomienie nie przedawkowało chloru - dobierz tę wartość do wydajności
Twojej pompki. Jeśli `countdown_code` nie jest ustawiony/wspierany przez
urządzenie, pompka zostanie włączona i **nie wyłączy się sama** - musisz
to zrobić ręcznie w apce.

## 4. Codzienny raport o 18:00 (cron)

```bash
bash scripts/install_cron.sh
```

Doda wpis do crontab: `0 18 * * * ... python -m delfin_monitor report`.
Logi trafiają do `data/cron.log`. Żeby usunąć wpis, edytuj `crontab -e`
ręcznie.

Urządzenie, na którym to uruchomisz, musi być włączone i mieć internet o
18:00, żeby cron zadziałał - np. komputer, Raspberry Pi, serwerek domowy albo
telefon (patrz sekcja 5 poniżej).

## 5. Uruchomienie na telefonie z Androidem (Termux)

Telefon jest dobrym wyborem, bo masz go zawsze przy sobie i online. Nie
używaj Termux z Google Play (nieaktualizowany) - zainstaluj z
[F-Droid](https://f-droid.org/packages/com.termux/).

1. Zainstaluj **Termux** i **Termux:Boot** (ta druga też z F-Droid - pozwala
   uruchomić usługę automatycznie po restarcie telefonu).
2. W Termux:
   ```bash
   pkg update && pkg upgrade
   pkg install python git cronie
   ```
3. Skopiuj na telefon folder `delfin_pool_monitor/` (np. `git clone` Twojego
   forka repo, albo `termux-setup-storage` i skopiowanie plików) i wykonaj
   kroki 1-4 z tego README (venv, `pip install -r requirements.txt`,
   `config.yaml`, CallMeBot).
4. Uruchom scheduler i zainstaluj wpis crontab:
   ```bash
   crond
   bash scripts/install_cron.sh
   ```
5. Żeby `crond` przeżył restart telefonu, dodaj jego start do Termux:Boot:
   ```bash
   mkdir -p ~/.termux/boot
   cat > ~/.termux/boot/start-crond.sh <<'EOF'
   #!/data/data/com.termux/files/usr/bin/sh
   crond
   EOF
   chmod +x ~/.termux/boot/start-crond.sh
   ```
6. W ustawieniach systemowych telefonu wyłącz **optymalizację baterii** dla
   Termux (Ustawienia → Aplikacje → Termux → Bateria → "Brak ograniczeń") -
   inaczej Android może ubić proces `crond` w tle i raport o 18:00 się nie
   wykona.
7. Opcjonalnie zainstaluj też `pkg install termux-api` + apkę Termux:API,
   jeśli chcesz kiedyś dodać natywne powiadomienia Android obok alarmów
   push.

## 5. Interaktywny dashboard (TUI)

```bash
python -m delfin_monitor tui
```

Skróty klawiszowe:
- `r` - pobierz nowy odczyt, zapisz do historii, wyślij alarm jeśli trzeba
- `t` - wyślij testowe powiadomienie
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
  cli.py            # komendy: report / discover / test-alert / pump-test / tui
  config.py         # wczytywanie config.yaml
  tuya_api.py       # niskopoziomowy klient Tuya Cloud API (HMAC, bez zaleznosci)
  sensor_client.py  # klient odczytow Tuya Cloud API (+ tryb mock)
  pump.py           # automatyczne wlaczanie pompki chloru
  thresholds.py     # ocena progow pH/chloru
  notifier.py       # alarmy push (ntfy.sh / WhatsApp CallMeBot)
  storage.py        # historia odczytow (data/history.jsonl)
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
