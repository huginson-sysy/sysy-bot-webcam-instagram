"""Insta-Bot Schwaltenweiher — Orchestrator.

Aufruf: python3 bot.py [--force] [--dry-run]
Cron-Empfehlung VPS: alle 30 Min zwischen 06:00 und 20:30.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from modules import quality, weather, caption, scheduler, poster, overlay, enhance


def log(record: dict) -> None:
    log_file = ROOT / "logs" / "bot.log"
    log_file.parent.mkdir(exist_ok=True)
    record["ts"] = datetime.now().isoformat(timespec="seconds")
    with log_file.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


def main() -> int:
    load_dotenv(ROOT / "config" / ".env")

    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Cooldown + Window ignorieren")
    p.add_argument("--dry-run", action="store_true", help="Erzwingt DRY_RUN=true")
    args = p.parse_args()

    dry = args.dry_run or os.getenv("DRY_RUN", "true").lower() == "true"

    webcam_url = os.environ["WEBCAM_URL"]

    # 1) Quality-Gate
    try:
        img = quality.fetch_image(webcam_url)
    except (quality.TruncatedSnapshot, OSError) as e:
        log({"event": "skip", "quality": None, "weather": None,
             "decision": {"post": False, "reasons": [f"snapshot_unavailable: {e}"]}})
        return 0
    q = quality.assess(img)

    # 2) Wetter (Open-Meteo, kein API-Key)
    lat = float(os.getenv("LAT", "47.5167"))
    lon = float(os.getenv("LON", "10.7000"))
    try:
        w = weather.score(weather.fetch(lat, lon))
    except weather.WeatherUnavailable as e:
        log({"event": "skip", "quality": q, "weather": None,
             "decision": {"post": False, "reasons": [f"weather_unavailable: {e}"]}})
        return 0

    # 3) Decision
    threshold = int(os.getenv("SCORE_THRESHOLD", "65"))
    cooldown_h = int(os.getenv("COOLDOWN_HOURS", "18"))
    window = (os.getenv("POST_WINDOW_START", "07:00"),
              os.getenv("POST_WINDOW_END", "20:00"))
    decision = scheduler.decide(w["score"], q["pass"], threshold, cooldown_h, window)

    if args.force:
        decision = {"post": True, "reasons": ["forced"], "state": decision["state"]}

    if not decision["post"]:
        log({"event": "skip", "quality": q, "weather": w, "decision": decision})
        return 0

    # 4) Caption
    cap = caption.build(w["main"], w["reasons"], seed=str(datetime.now().date()))

    # 5) Upscale/Schärfung, dann Overlay komponieren + speichern
    composed = overlay.compose(enhance.enhance(img), w)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    post_dir = Path(os.getenv("POST_DIR", str(ROOT / "logs" / "posts")))
    post_url_base = os.getenv("POST_URL_BASE",
                              "https://schwaltenweiher.de/webcam")
    file_name = f"post_{ts}.jpg"
    out_path = post_dir / file_name
    overlay.save(composed, out_path)
    image_url = f"{post_url_base.rstrip('/')}/{file_name}"

    # 6) Cleanup — nur 30 letzte Posts behalten (Snapshot-Rotation)
    posts = sorted(post_dir.glob("post_*.jpg"))
    for old in posts[:-30]:
        try:
            old.unlink()
        except OSError:
            pass

    # 7) Post auf Insta — Container-Timeout o.ae. sauber abfangen statt Crash.
    #    mark_posted wird erst in Schritt 8 gesetzt → bei Fehler bleibt der
    #    Cooldown offen und der naechste Cron-Tick versucht es automatisch neu.
    try:
        result = poster.post(image_url, cap, dry_run=dry)
    except poster.PosterError as e:
        log({"event": "error", "quality": q, "weather": w, "caption": cap,
             "image_url": image_url,
             "decision": {"post": False, "reasons": [f"poster_error: {e}"]}})
        return 0

    # 8) Crosspost auf FB-Page (ohne Hashtags-Spam, kürzere Caption)
    fb_result = None
    if not dry and result.get("media_id"):
        scheduler.mark_posted(w["score"])
        fb_caption = cap.split("\n\n")[0]  # nur Hauptzeile, keine #tags
        try:
            fb_result = poster.post_to_facebook(image_url, fb_caption, dry_run=False)
        except poster.PosterError as e:
            fb_result = {"error": str(e)}

    log({
        "event": "post" if not dry else "would_post",
        "quality": q,
        "weather": w,
        "caption": cap,
        "image_url": image_url,
        "result": result,
        "fb_result": fb_result,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
