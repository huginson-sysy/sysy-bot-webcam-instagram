"""Smoke-Test ohne echte API-Calls — Logik-Checks."""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from modules import caption, scheduler


def test_caption_builds():
    out = caption.build("Clear", ["klarer Himmel"], seed="t1")
    assert "schwaltenweiher" in out.lower()
    assert "#" in out
    print("caption OK:", out[:80])


def test_scheduler_window():
    inside = scheduler.in_window(datetime(2026, 5, 5, 14, 0), "07:00", "20:00")
    outside = scheduler.in_window(datetime(2026, 5, 5, 23, 0), "07:00", "20:00")
    assert inside and not outside
    print("scheduler window OK")


def test_decide_below_threshold():
    d = scheduler.decide(weather_score=30, quality_pass=True, threshold=65,
                         cooldown_h=18, window=("07:00", "20:00"),
                         now=datetime(2026, 5, 5, 14, 0))
    assert not d["post"]
    assert any("threshold" in r for r in d["reasons"])
    print("decide threshold OK")


if __name__ == "__main__":
    test_caption_builds()
    test_scheduler_window()
    test_decide_below_threshold()
    print("ALL OK")
