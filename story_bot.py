"""Story-Bot Schwaltenweiher — eigener Orchestrator für Insta Stories.

Eigenständig zu bot.py (Feed). Eigener Threshold + Cooldown.
Aufruf: python3 story_bot.py [--force] [--dry-run]
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

from modules import quality, weather, scheduler, poster, overlay, enhance
from modules import story as story_mod


def log(record: dict) -> None:
    log_file = ROOT / "logs" / "story.log"
    log_file.parent.mkdir(exist_ok=True)
    record["ts"] = datetime.now().isoformat(timespec="seconds")
    with log_file.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


def main() -> int:
    load_dotenv(ROOT / "config" / ".env")

    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    dry = args.dry_run or os.getenv("DRY_RUN", "true").lower() == "true"

    webcam_url = os.environ["WEBCAM_URL"]
    try:
        img = quality.fetch_image(webcam_url)
    except (quality.TruncatedSnapshot, OSError) as e:
        log({"event": "skip", "quality": None, "weather": None,
             "decision": {"post": False, "reasons": [f"snapshot_unavailable: {e}"]}})
        return 0
    q = quality.assess(img)

    lat = float(os.getenv("LAT", "47.5167"))
    lon = float(os.getenv("LON", "10.7000"))
    try:
        w = weather.score(weather.fetch(lat, lon))
    except weather.WeatherUnavailable as e:
        log({"event": "skip_story", "quality": q, "weather": None,
             "decision": {"post": False, "reasons": [f"weather_unavailable: {e}"]}})
        return 0

    threshold = int(os.getenv("STORY_THRESHOLD", "50"))
    cooldown_h = int(os.getenv("STORY_COOLDOWN_HOURS", "8"))
    window = (os.getenv("POST_WINDOW_START", "07:00"),
              os.getenv("POST_WINDOW_END", "20:00"))
    decision = scheduler.decide(
        w["score"], q["pass"], threshold, cooldown_h, window,
        cooldown_key="last_story_iso",
    )

    if args.force:
        decision = {"post": True, "reasons": ["forced"], "state": decision["state"]}

    if not decision["post"]:
        log({"event": "skip_story", "quality": q, "weather": w, "decision": decision})
        return 0

    composed = story_mod.compose_story(enhance.enhance(img), w, layout="C")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    post_dir = Path(os.getenv("POST_DIR", str(ROOT / "logs" / "posts")))
    post_url_base = os.getenv("POST_URL_BASE",
                              "https://schwaltenweiher.de/webcam")
    file_name = f"story_{ts}.jpg"
    out_path = post_dir / file_name
    overlay.save(composed, out_path)
    image_url = f"{post_url_base.rstrip('/')}/{file_name}"

    # Cleanup — letzte 30 Stories behalten
    stories = sorted(post_dir.glob("story_*.jpg"))
    for old in stories[:-30]:
        try:
            old.unlink()
        except OSError:
            pass

    # Container-Timeout o.ae. sauber abfangen statt Crash; mark_posted folgt
    # erst danach → bei Fehler retried der naechste Cron-Tick automatisch.
    try:
        result = poster.post_story(image_url, dry_run=dry)
    except poster.PosterError as e:
        log({"event": "error_story", "quality": q, "weather": w,
             "image_url": image_url,
             "decision": {"post": False, "reasons": [f"poster_error: {e}"]}})
        return 0

    fb_result = None
    if not dry and result.get("media_id"):
        scheduler.mark_posted(w["score"], key="last_story_iso",
                              score_key="last_story_score")
        try:
            fb_result = poster.post_fb_story(image_url, dry_run=False)
        except poster.PosterError as e:
            fb_result = {"error": str(e)}

    log({
        "event": "story" if not dry else "would_story",
        "quality": q,
        "weather": w,
        "image_url": image_url,
        "result": result,
        "fb_result": fb_result,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
