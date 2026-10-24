"""Wetter-Score 0–100 via Open-Meteo (kein API-Key, kostenlos).

Open-Meteo liefert WMO-Wettercodes, current+daily Block.
Doku: https://open-meteo.com/en/docs
"""
import time as _time
from datetime import datetime, timezone
import requests


class WeatherUnavailable(Exception):
    """Open-Meteo nach Retries nicht erreichbar — Aufrufer soll skippen."""


# WMO Weather Code → (label, base_score)
WMO = {
    0: ("klarer Himmel", 88),
    1: ("überwiegend klar", 80),
    2: ("teilweise bewölkt", 70),
    3: ("bedeckt", 50),
    45: ("Nebel", 20),
    48: ("Reifnebel", 22),
    51: ("leichter Nieselregen", 28),
    53: ("Nieselregen", 25),
    55: ("starker Nieselregen", 22),
    56: ("gefrierender Niesel", 30),
    57: ("gefrierender Niesel", 30),
    61: ("leichter Regen", 25),
    63: ("Regen", 20),
    65: ("starker Regen", 18),
    66: ("gefrierender Regen", 30),
    67: ("gefrierender Regen", 30),
    71: ("leichter Schneefall", 80),
    73: ("Schneefall", 88),
    75: ("starker Schneefall", 92),
    77: ("Schneegriesel", 70),
    80: ("Regenschauer", 30),
    81: ("Regenschauer", 28),
    82: ("starke Regenschauer", 25),
    85: ("Schneeschauer", 82),
    86: ("starke Schneeschauer", 88),
    95: ("Gewitter", 72),
    96: ("Gewitter mit Hagel", 75),
    99: ("Gewitter mit Hagel", 75),
}


def fetch(lat: float, lon: float, retries: int = 3, backoff: float = 2.0) -> dict:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,weather_code,cloud_cover,is_day",
                    "daily": "sunrise,sunset",
                    "timezone": "Europe/Berlin",
                },
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, requests.HTTPError) as e:
            last_err = e
            if attempt < retries - 1:
                _time.sleep(backoff * (attempt + 1))
    raise WeatherUnavailable(f"Open-Meteo nach {retries} Versuchen nicht erreichbar: {last_err}")


def score(w: dict) -> dict:
    cur = w["current"]
    code = cur["weather_code"]
    clouds = cur["cloud_cover"]
    is_day = bool(cur["is_day"])
    label, base = WMO.get(code, ("unklar", 30))

    s = base
    reasons = [label]

    # Goldene Stunde Bonus
    daily = w["daily"]
    sunrise = datetime.fromisoformat(daily["sunrise"][0]).timestamp()
    sunset = datetime.fromisoformat(daily["sunset"][0]).timestamp()
    now = datetime.now(timezone.utc).astimezone().timestamp()

    if abs(now - sunrise) < 1800:
        s += 12
        reasons.append("Sonnenaufgang")
    if abs(now - sunset) < 1800:
        s += 15
        reasons.append("Sonnenuntergang")

    # Wolken-Differenzierung bei "bedeckt": Lücken sichtbar -> Bonus
    if code == 3 and clouds < 70:
        s += 10
        reasons.append("Wolkenlücken")

    # Tageswärme-Bonus
    if is_day and cur["temperature_2m"] >= 15:
        s += 5
        reasons.append("warm")

    # Nacht-Penalty
    if not is_day:
        s = max(0, s - 30)
        reasons.append("Nacht")

    s = max(0, min(100, s))
    return {
        "score": s,
        "main": _main(code),
        "label": label,
        "code": code,
        "temp": cur["temperature_2m"],
        "clouds": clouds,
        "is_day": is_day,
        "reasons": reasons,
    }


def _main(code: int) -> str:
    """Mappt WMO-Code auf einfache Kategorie für Caption-Templates."""
    if code == 0:
        return "Clear"
    if code in (1, 2):
        return "Clear"
    if code == 3:
        return "Clouds"
    if code in (45, 48):
        return "Fog"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorm"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "Rain"
    return "Clouds"


if __name__ == "__main__":
    import json, os
    lat = float(os.getenv("LAT", "47.5167"))
    lon = float(os.getenv("LON", "10.7000"))
    print(json.dumps(score(fetch(lat, lon)), indent=2, ensure_ascii=False))
