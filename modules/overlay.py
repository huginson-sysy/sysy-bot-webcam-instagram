"""Overlay-Komposition: Footer-Strip + Brand-Stempel oben links.

Layout:
┌────────────────────────────────┐
│ ◉ LIVE                         │ ← top-left brand chip
│                                │
│         [Webcam-Bild]          │
│                                │
│                                │
│   SCHWALTENWEIHER · 14°C ·     │ ← bottom strip, halbtransparent
│   bedeckt · 06.05. 12:34       │
└────────────────────────────────┘
"""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# Font-Suche: erst System-Fonts auf Linux/Mac, fallback auf default
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",      # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",           # Linux regular
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",         # macOS
    "/System/Library/Fonts/Helvetica.ttc",                       # macOS
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def compose(img: Image.Image, weather: dict) -> Image.Image:
    """Webcam-Bild + Overlay. weather erwartet temp, label."""
    img = img.convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # === Bottom Strip ===
    strip_h = max(60, H // 14)
    d.rectangle([0, H - strip_h, W, H], fill=(0, 0, 0, 165))

    temp = round(weather.get("temp", 0))
    label = weather.get("label", "")
    ts = datetime.now().strftime("%d.%m. %H:%M")
    main = f"SCHWALTENWEIHER · LIVE"
    sub = f"{temp}°C · {label} · {ts}"

    main_font = _font(int(strip_h * 0.42))
    sub_font = _font(int(strip_h * 0.30))

    pad = int(strip_h * 0.30)
    d.text((pad, H - strip_h + pad // 2), main,
           fill=(255, 255, 255, 255), font=main_font)
    main_h = main_font.size + 4
    d.text((pad, H - strip_h + pad // 2 + main_h), sub,
           fill=(220, 220, 220, 255), font=sub_font)

    # === Top-Left Live-Chip ===
    chip_pad_x, chip_pad_y = 14, 8
    chip_text = "● LIVE"
    chip_font = _font(int(strip_h * 0.32))
    bbox = chip_font.getbbox(chip_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    chip_w = tw + chip_pad_x * 2
    chip_h = th + chip_pad_y * 2
    d.rounded_rectangle([20, 20, 20 + chip_w, 20 + chip_h],
                        radius=chip_h // 2, fill=(220, 38, 38, 220))
    d.text((20 + chip_pad_x, 20 + chip_pad_y - 2), chip_text,
           fill=(255, 255, 255, 255), font=chip_font)

    return Image.alpha_composite(img, overlay).convert("RGB")


def save(img: Image.Image, out_path: Path, quality: int = 92) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=quality, optimize=True)
    return out_path


if __name__ == "__main__":
    import os, sys, requests
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "WEBCAM_URL",
        "https://schwaltenweiher.de/webcam/schwaltenweiher_latest.jpg",
    )
    r = requests.get(url, timeout=10)
    base = Image.open(BytesIO(r.content))
    weather = {"temp": 14.5, "label": "bedeckt"}
    out = compose(base, weather)
    save(out, Path("logs/preview.jpg"))
    print("OK → logs/preview.jpg")
