"""Story-Komposition: 1080x1920 mit Webcam zentriert auf blurred Background.

Layout A:
┌────────────────┐ 1080
│ ░░░░░░░░░░░░░░ │  ← blurred BG (gleiches Bild)
│ ░░░░░░░░░░░░░░ │
│ ░ ● LIVE      ░│  ← chip top-left
│ ░░░░░░░░░░░░░░ │
│ ┌──────────┐ ░ │
│ │  Webcam  │   │  ← scharfes Bild zentriert
│ └──────────┘   │
│ ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░░░░░ │
│ SCHWALTENWEIHER│  ← bottom strip
│ 14°C · bedeckt │
└────────────────┘ 1920
"""
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import overlay


STORY_W = 1080
STORY_H = 1920


def compose_story(img: Image.Image, weather: dict, layout: str = "A") -> Image.Image:
    img = img.convert("RGB")

    if layout == "C":
        # Vollbild gecroppt, schwarzer Verlauf oben + unten für Lesbarkeit
        canvas = _cover_resize(img, STORY_W, STORY_H)
        grad = _vertical_gradient(STORY_W, STORY_H)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), grad).convert("RGB")
    else:
        # Layout A: Blurred Background + zentriertes Bild
        bg = img.copy()
        bg = _cover_resize(bg, STORY_W, STORY_H)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
        tint = Image.new("RGB", (STORY_W, STORY_H), (0, 0, 0))
        bg = Image.blend(bg, tint, alpha=0.35)
        fg = _fit_resize(img, STORY_W - 80, int(STORY_H * 0.55))
        fg_x = (STORY_W - fg.width) // 2
        fg_y = (STORY_H - fg.height) // 2 - 40
        canvas = bg.copy()
        canvas.paste(fg, (fg_x, fg_y))

    # === Overlay: Live-Chip + Bottom-Block ===
    overlay_layer = Image.new("RGBA", (STORY_W, STORY_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay_layer)

    # Top-Left LIVE Chip
    chip_font = overlay._font(46)
    chip_text = "● LIVE"
    bbox = chip_font.getbbox(chip_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    chip_pad_x, chip_pad_y = 22, 12
    chip_w = tw + chip_pad_x * 2
    chip_h = th + chip_pad_y * 2
    cx, cy = 60, 80
    d.rounded_rectangle([cx, cy, cx + chip_w, cy + chip_h],
                        radius=chip_h // 2, fill=(220, 38, 38, 230))
    d.text((cx + chip_pad_x, cy + chip_pad_y - 4), chip_text,
           fill=(255, 255, 255, 255), font=chip_font)

    # Bottom-Block: Titel groß, Wetter darunter
    if layout == "C":
        block_top = STORY_H - 320
    else:
        block_top = fg_y + fg.height + 60
    title_font = overlay._font(70)
    sub_font = overlay._font(44)
    cta_font = overlay._font(36)

    title = "SCHWALTENWEIHER"
    temp = round(weather.get("temp", 0))
    label = weather.get("label", "")
    sub = f"{temp}°C · {label}"
    cta = datetime.now().strftime("%d.%m.%Y · %H:%M Uhr")

    # zentriert
    for text, font, y_off, color in [
        (title, title_font, 0, (255, 255, 255, 255)),
        (sub, sub_font, 95, (240, 240, 240, 255)),
        (cta, cta_font, 165, (200, 200, 200, 230)),
    ]:
        bb = font.getbbox(text)
        w = bb[2] - bb[0]
        d.text(((STORY_W - w) // 2, block_top + y_off), text,
               fill=color, font=font)

    final = Image.alpha_composite(canvas.convert("RGBA"), overlay_layer)
    return final.convert("RGB")


def _cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    """Skaliert + croppt sodass Bild w×h voll ausfüllt."""
    src_ratio = img.width / img.height
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        new_h = h
        new_w = int(h * src_ratio)
    else:
        new_w = w
        new_h = int(w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _fit_resize(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Skaliert sodass Bild komplett in max_w×max_h passt (Letterbox)."""
    ratio = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    return img.resize((new_w, new_h), Image.LANCZOS)


def _vertical_gradient(w: int, h: int) -> Image.Image:
    """Schwarzer Verlauf oben (für Chip) und unten (für Text-Block)."""
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = grad.load()
    top_h = int(h * 0.18)
    bot_h = int(h * 0.32)
    for y in range(top_h):
        a = int(180 * (1 - y / top_h))
        for x in range(w):
            px[x, y] = (0, 0, 0, a)
    for y in range(h - bot_h, h):
        a = int(200 * ((y - (h - bot_h)) / bot_h))
        for x in range(w):
            px[x, y] = (0, 0, 0, a)
    return grad


if __name__ == "__main__":
    import os, sys, requests
    from io import BytesIO
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "WEBCAM_URL",
        "https://schwaltenweiher.de/webcam/schwaltenweiher_latest.jpg",
    )
    r = requests.get(url, timeout=10)
    base = Image.open(BytesIO(r.content))
    weather = {"temp": 14.5, "label": "bedeckt"}
    layout = sys.argv[2] if len(sys.argv) > 2 else "A"
    out = compose_story(base, weather, layout=layout)
    out_path = Path(f"logs/preview_story_{layout}.jpg")
    overlay.save(out, out_path)
    print(f"OK → {out_path} ({out.size[0]}×{out.size[1]})")
