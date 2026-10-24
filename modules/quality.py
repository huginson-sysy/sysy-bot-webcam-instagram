"""Bild-Quality-Gate: Helligkeit, Schärfe, Tageslicht, Truncation."""
import time
from io import BytesIO
from PIL import Image, ImageStat, ImageFilter, ImageFile
import requests

# Tolerant laden, damit truncated Bilder NICHT crashen — wir validieren danach
# explizit per EOI-Marker und Bottom-Half-Variance.
ImageFile.LOAD_TRUNCATED_IMAGES = True


class TruncatedSnapshot(Exception):
    pass


def _is_complete_jpeg(content: bytes) -> bool:
    """JPEG-Dateien enden mit dem End-Of-Image-Marker FFD9."""
    return len(content) > 4 and content.rstrip(b"\x00").endswith(b"\xff\xd9")


def fetch_image(url: str, timeout: int = 10, retries: int = 3) -> Image.Image:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            if not _is_complete_jpeg(r.content):
                raise TruncatedSnapshot(
                    f"JPEG ohne EOI-Marker (attempt {attempt + 1}, {len(r.content)} bytes)"
                )
            img = Image.open(BytesIO(r.content))
            img.load()
            return img.convert("RGB")
        except (OSError, TruncatedSnapshot, requests.RequestException) as e:
            last_err = e
            if attempt < retries:
                time.sleep(2)
    raise last_err  # type: ignore[misc]


def brightness(img: Image.Image) -> float:
    """0–255, Mittelwert über Graustufen."""
    return ImageStat.Stat(img.convert("L")).mean[0]


def sharpness(img: Image.Image) -> float:
    """Varianz nach Laplace-Filter — höher = schärfer. Threshold ~40."""
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    return ImageStat.Stat(edges).stddev[0]


def color_variance(img: Image.Image) -> float:
    """Niedrig = Nebel/Whiteout. Threshold ~15."""
    s = ImageStat.Stat(img)
    return sum(s.stddev) / 3


def half_variance(img: Image.Image) -> tuple[float, float]:
    """color_variance fuer obere und untere Bildhaelfte separat.

    Erkennt halb-graue Snapshots (FTP-Race) — der nicht geschriebene Bereich
    wird von PIL mit Nullen aufgefuellt und hat color_var nahe 0.
    """
    w, h = img.size
    top = img.crop((0, 0, w, h // 2))
    bottom = img.crop((0, h // 2, w, h))
    cv_top = sum(ImageStat.Stat(top).stddev) / 3
    cv_bot = sum(ImageStat.Stat(bottom).stddev) / 3
    return round(cv_top, 1), round(cv_bot, 1)


def assess(img: Image.Image) -> dict:
    b = brightness(img)
    sh = sharpness(img)
    cv = color_variance(img)
    cv_top, cv_bot = half_variance(img)
    reasons = []
    if b < 40:
        reasons.append(f"zu dunkel ({b:.0f})")
    if b > 230:
        reasons.append(f"überbelichtet ({b:.0f})")
    if sh < 25:
        reasons.append(f"unscharf ({sh:.0f})")
    if cv < 12:
        reasons.append(f"flach/Nebel ({cv:.0f})")
    if cv_bot < 5 or cv_top < 5:
        reasons.append(f"halb-tot (top={cv_top}, bot={cv_bot})")
    elif min(cv_top, cv_bot) < 0.25 * max(cv_top, cv_bot):
        reasons.append(f"haelften-asymmetrisch (top={cv_top}, bot={cv_bot})")
    return {
        "brightness": round(b, 1),
        "sharpness": round(sh, 1),
        "color_var": round(cv, 1),
        "cv_top": cv_top,
        "cv_bot": cv_bot,
        "pass": len(reasons) == 0,
        "reasons": reasons,
    }


if __name__ == "__main__":
    import os, sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "WEBCAM_URL",
        "https://schwaltenweiher.de/webcam/schwaltenweiher_latest.jpg",
    )
    print(json.dumps(assess(fetch_image(url)), indent=2, ensure_ascii=False))
