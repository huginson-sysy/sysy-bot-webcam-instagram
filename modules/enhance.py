# ╔══════════════════════════════════╗
# ║      ᚺ  ᚢ  ᚷ  ᛁ  ᚾ  ᛋ  ᛟ  ᚾ      ║
# ║         H  U  G  I  N  S  O  N    ║
# ╚══════════════════════════════════╝
# HUGINSON · Synthetic Syndicate · 2026-05-30
"""Bild-Upscaler + Schärfung (Lanczos-Supersampling).

Kein AI, kein torch — nur Pillow-Bordmittel. ~0.3s pro Bild, vernachlässigbare
VPS-Last. Idee: Bild per Lanczos hochziehen, auf der größeren Auflösung schärfen
und Tonwerte anheben. Das finale Resize in overlay/story arbeitet dann mit mehr
Pixeln → wahrgenommen schärferes Endbild (klassisches Supersampling).

Erfindet keine echten Details — hebt nur vorhandene hervor.

ENV:
- ENHANCE         "true"/"false" (default true) — Modul global an/aus
- ROTATE_DEG      float (default 0.0) — Bild geraderichten (+ = gegen Uhrzeiger);
                  schräge Ränder werden auto-weggecroppt (leichter Zoom)
- UPSCALE_FACTOR  float (default 2.0) — 1.0 = kein Hochskalieren, nur schärfen
- UPSCALE_MAX_PX  int (default 4096) — längste Kante deckeln (Speicher-Schutz)
- SHARPEN_PERCENT int (default 120) — UnsharpMask-Stärke
- ENH_CONTRAST    float (default 1.05)
- ENH_COLOR       float (default 1.08) — Sättigung
"""
import math
import os

from PIL import Image, ImageEnhance, ImageFilter


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _straighten(img: Image.Image, deg: float) -> Image.Image:
    """Rotiert um deg° und croppt die schrägen Schwarzränder weg.

    Croppt den größten zentrierten Rahmen mit Original-Seitenverhältnis und
    skaliert zurück auf Originalgröße (leichter Zoom als Nebeneffekt)."""
    w, h = img.size
    rotated = img.rotate(deg, resample=Image.BICUBIC, expand=False)
    a = math.radians(abs(deg))
    scale = math.cos(a) + (h / w) * math.sin(a)  # konservativer Crop-Faktor
    cw, ch = int(w / scale), int(h / scale)
    left, top = (w - cw) // 2, (h - ch) // 2
    return rotated.crop((left, top, left + cw, top + ch)).resize((w, h), Image.LANCZOS)


def enhance(img: Image.Image) -> Image.Image:
    """Geraderichten + Upscale + Schärfung. Bei ENHANCE=false Bild unverändert."""
    if os.getenv("ENHANCE", "true").lower() != "true":
        return img

    img = img.convert("RGB")

    # 0) Geraderichten (schiefe Kamerahalterung kompensieren)
    rotate_deg = _env_float("ROTATE_DEG", 0.0)
    if abs(rotate_deg) > 0.01:
        img = _straighten(img, rotate_deg)

    factor = _env_float("UPSCALE_FACTOR", 2.0)
    max_px = _env_int("UPSCALE_MAX_PX", 4096)

    # 1) Lanczos-Upscale (mit Deckel auf längster Kante)
    if factor > 1.0:
        target_long = min(int(max(img.size) * factor), max_px)
        scale = target_long / max(img.size)
        if scale > 1.0:
            new_size = (round(img.width * scale), round(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)

    # 2) Schärfen auf der (größeren) Auflösung — Lanczos zeichnet leicht weich
    percent = _env_int("SHARPEN_PERCENT", 120)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=percent, threshold=3))

    # 3) Tonwerte dezent anheben (Kontrast + Sättigung)
    img = ImageEnhance.Contrast(img).enhance(_env_float("ENH_CONTRAST", 1.05))
    img = ImageEnhance.Color(img).enhance(_env_float("ENH_COLOR", 1.08))

    return img


if __name__ == "__main__":
    import sys
    from io import BytesIO
    import requests

    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "WEBCAM_URL",
        "https://schwaltenweiher.de/webcam/schwaltenweiher_latest.jpg",
    )
    r = requests.get(url, timeout=10)
    src = Image.open(BytesIO(r.content)).convert("RGB")
    out = enhance(src)
    out.save("logs/preview_enhanced.jpg", "JPEG", quality=92, optimize=True)
    print(f"OK  {src.size} → {out.size}  → logs/preview_enhanced.jpg")
