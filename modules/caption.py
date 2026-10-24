"""Caption-Generator — menschen-artig, variabel.

Variante 1: Lokal-Templates mit Platzhaltern + Emoji-Pool.
Variante 2 (später): Ollama-Call gegen lokales Model für mehr Variation.
"""
import random
from datetime import datetime


HASHTAGS_CORE = [
    "#schwaltenweiher",
    "#füssen",
    "#allgäu",
    "#bayern",
]

HASHTAGS_POOL = [
    "#bergsee",
    "#wandern",
    "#biergarten",
    "#alpen",
    "#ostallgäu",
    "#urlaubinbayern",
    "#visitbavaria",
    "#allgäuliebe",
    "#naturpur",
    "#bergliebe",
    "#schwangau",
    "#hopfensee",
    "#forggensee",
    "#füssenimallgäu",
]


TEMPLATES = {
    "klarer Himmel": [
        "Tag wie gemalt. Kein Wölkchen. {time_phrase}",
        "Blauer Himmel, klare Sicht — {time_phrase}",
        "So sieht's grad aus. {time_phrase}",
        "Sonne satt am See. {time_phrase}",
    ],
    "Sonnenuntergang": [
        "Letztes Licht über'm See.",
        "Wenn die Berge rosa werden.",
        "Feierabend-Stimmung am Schwaltenweiher.",
        "Goldene Stunde, frisch gezapft.",
    ],
    "Sonnenaufgang": [
        "Erste Sonnenstrahlen über'm See.",
        "Guten Morgen vom Schwaltenweiher.",
        "Bevor die Welt aufwacht.",
    ],
    "Schnee": [
        "Frisch zugedeckt.",
        "Winterruhe am See.",
        "Schnee bis ans Ufer.",
        "So ruhig. So weiß.",
    ],
    "Gewitter": [
        "Petrus dreht auf.",
        "Spektakel überm See.",
    ],
    "leicht bewölkt": [
        "Mal Sonne, mal Wolke. {time_phrase}",
        "Wechselhaft, aber schön. {time_phrase}",
    ],
    "default": [
        "Schwaltenweiher live. {time_phrase}",
        "Aktueller Blick. {time_phrase}",
    ],
}


def time_phrase() -> str:
    h = datetime.now().hour
    if 5 <= h < 10:
        return "Frischer Morgen."
    if 10 <= h < 13:
        return "Vormittag am See."
    if 13 <= h < 17:
        return "Nachmittag, perfekt für eine Runde."
    if 17 <= h < 21:
        return "Feierabend."
    return "Abendstimmung."


def hashtags(seed: str | None = None) -> str:
    rng = random.Random(seed)
    extra = rng.sample(HASHTAGS_POOL, k=rng.randint(4, 6))
    return " ".join(HASHTAGS_CORE + extra)


def build(weather_main: str, reasons: list[str], seed: str | None = None) -> str:
    rng = random.Random(seed)
    key = "default"
    for r in reasons:
        if r in TEMPLATES:
            key = r
            break
    if key == "default":
        if weather_main == "Snow":
            key = "Schnee"
        elif weather_main == "Thunderstorm":
            key = "Gewitter"
        elif weather_main in TEMPLATES:
            key = weather_main
    line = rng.choice(TEMPLATES[key]).format(time_phrase=time_phrase())
    return f"{line}\n\n{hashtags(seed)}"


if __name__ == "__main__":
    print(build("Clear", ["klarer Himmel"]))
    print("---")
    print(build("Snow", ["Schnee"]))
    print("---")
    print(build("Clear", ["Sonnenuntergang"]))
