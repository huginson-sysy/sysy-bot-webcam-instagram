"""Posting-Entscheidung: Cooldown + Tageszeit-Window + Score-Threshold."""
import json
from datetime import datetime, time, timedelta
from pathlib import Path


STATE_FILE = Path(__file__).parent.parent / "logs" / "state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_post_iso": None, "last_score": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def in_window(now: datetime, start: str, end: str) -> bool:
    s = time.fromisoformat(start)
    e = time.fromisoformat(end)
    n = now.time()
    return s <= n <= e


def cooldown_ok(state: dict, hours: int, now: datetime,
                key: str = "last_post_iso") -> bool:
    if not state.get(key):
        return True
    last = datetime.fromisoformat(state[key])
    return now - last > timedelta(hours=hours)


def decide(weather_score: int, quality_pass: bool, threshold: int,
           cooldown_h: int, window: tuple[str, str],
           now: datetime | None = None,
           cooldown_key: str = "last_post_iso") -> dict:
    now = now or datetime.now()
    state = load_state()
    reasons = []
    if not quality_pass:
        reasons.append("quality_fail")
    if weather_score < threshold:
        reasons.append(f"score_below_threshold ({weather_score}<{threshold})")
    if not in_window(now, *window):
        reasons.append(f"outside_window ({now.strftime('%H:%M')} ∉ {window[0]}-{window[1]})")
    if not cooldown_ok(state, cooldown_h, now, key=cooldown_key):
        reasons.append(f"cooldown_active (last {state.get(cooldown_key)})")
    return {"post": len(reasons) == 0, "reasons": reasons, "state": state}


def mark_posted(score: int, now: datetime | None = None,
                key: str = "last_post_iso", score_key: str = "last_score") -> None:
    now = now or datetime.now()
    state = load_state()
    state[key] = now.isoformat()
    state[score_key] = score
    save_state(state)
