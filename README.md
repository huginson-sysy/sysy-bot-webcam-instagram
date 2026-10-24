<!--
╔══════════════════════════════════╗
║      ᚺ  ᚢ  ᚷ  ᛁ  ᚾ  ᛋ  ᛟ  ᚾ      ║
║         H  U  G  I  N  S  O  N    ║
╚══════════════════════════════════╝
-->
# Webcam-Instagram-Bot

Postet automatisch Webcam-Bilder auf Instagram (und die verbundene Facebook-Seite), wenn das Wetter
sehenswert ist: Snapshot holen → Bildqualität prüfen → Wetter bewerten → Bildtext erzeugen → posten.
Entstanden für das Restaurant Schwaltenweiher am Weiher in Seeg (Allgäu), seit Mai 2026 täglich im Betrieb.

```
Webcam-Snapshot ──► Quality-Gate ──► Wetter-Score ──► Caption ──► Post-Entscheid ──► Meta Graph API
                    (Helligkeit,     (Sonne, Schnee,  (Vorlagen,  (Cooldown,
                     Schärfe, Tag)    Sonnenuntergang)  Varianten)  Zeitfenster, Schwelle)
```

## Module

| Datei | Zweck |
|---|---|
| `bot.py` | Orchestrator für Feed-Posts |
| `story_bot.py` | Stories (eigene Schwelle und eigener Cooldown) |
| `modules/weather.py` | Wetter-Score 0–100 aus Open-Meteo |
| `modules/quality.py` | Bildprüfung mit Pillow (Helligkeit, Schärfe, Tageslicht) |
| `modules/enhance.py`, `modules/overlay.py` | Aufwertung (Upscale, Schärfung, Geraderichten) und Overlay |
| `modules/caption.py` | Bildtexte mit Varianten |
| `modules/scheduler.py` | Cooldown, Tageszeitfenster, Schwellen |
| `modules/poster.py` | Meta Graph API: Bild-URL + Text → `creation_id` → `publish` |
| `run.sh`, `run_story.sh` | Cron-Wrapper mit Logrotation |
| `deploy.sh` | rsync auf den Server (`DEPLOY_HOST=root@<host> ./deploy.sh`), `.env` bleibt auf dem Server |
| `tests/test_smoke.py` | Logik-Tests ohne API-Aufrufe |

## Einrichtung

1. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. `cp config/.env.example config/.env` und ausfüllen: Meta-App (App-ID, App-Secret, Page-ID, IG-User-ID,
   Page-Token mit `instagram_content_publish`), `WEBCAM_URL` (öffentlich erreichbares JPEG), `LAT`/`LON`,
   Schwellen und Zeitfenster. `DRY_RUN=true` postet nichts und schreibt nur ins Log.
3. Probe: `.venv/bin/python bot.py` (mit `DRY_RUN=true`), dann Cron, z. B. alle 30 Minuten `./run.sh`.

Die Meta Graph API verlangt eine öffentlich erreichbare Bild-URL; der Bot lädt kein Bild hoch, sondern übergibt die URL.

## Hinweise

- Der Betreiber braucht die Rechte am Webcam-Bild und ein Instagram-Business-/Creator-Konto mit verbundener Facebook-Seite.
- Open-Meteo: Daten CC BY 4.0, API für nicht-kommerzielle Nutzung frei.
- Token und Zugangsdaten nur in `config/.env` (gitignored).

## Lizenz

**MIT** — siehe [LICENSE](LICENSE). © 2026 Daniel Lenzenhuber (HUGINSON).
