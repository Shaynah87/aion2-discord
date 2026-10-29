
"""
Nyerk24 · Halloween 2026

Originalbanner unverändert: 1200 × 180 Pixel.
Keine Skalierung, kein Zuschneiden, keine neuen Motive.

Größerer Halloween-Schriftzug mit Feuer- und Risseffekt.
Die neun Eventbereiche bleiben vollständig erhalten.
"""

import io
import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageFilter


EVENT = {
    "id": "halloween_2026",
    "name": "Halloween",
    "timezone": "Europe/Berlin",
    "start": "2026-10-14T00:00:00+02:00",
    "end": "2026-11-04T09:00:00+01:00",
    "date_label": "14.10. – 04.11.2026",
    "image": "Events/Halloween/halloween.png",
    "currency": "Halloween-Kürbismünze (Event)",
    "source_url": "https://aion2.plaync.com/de-de/eventon/board/event_notice/view?articleId=6acf216807b77e214688a773",
    "sections": [
        {
            "title": "🎃 Süßes oder Saures – Anwesenheit",
            "description": "Tägliche Anmeldung über das Eventmenü. Belohnung: Halloween-Kürbismünzen (Event).",
            "entries": [
                {"days": "1–6", "coins_per_day": 35},
                {"days": "7", "coins_per_day": 100},
                {"days": "8–13", "coins_per_day": 35},
                {"days": "14", "coins_per_day": 100},
            ],
        },
        {
            "title": "⚔️ Saisonmissionen – Event",
            "description": "Im Spiel unter [Saisonmission] > [Event]. Einmal pro Woche pro Server. Belohnungen jeweils in Halloween-Kürbismünzen (Event).",
            "entries": [
                {"name": "Abyssus", "task": "10 Monster im Abyssus jagen", "coins": 25},
                {"name": "Transzendenz", "task": "1-mal den Transzendenz-Dungeon abschließen", "coins": 25},
                {"name": "Expedition", "task": "1-mal die Expeditions-Eroberung abschließen", "coins": 25},
                {"name": "Aszensusritus", "task": "1-mal den Aszensusritus abschließen", "coins": 25},
                {"name": "Albtraum", "task": "1-mal abschließen (beliebige Stufe)", "coins": 25},
                {"name": "Anmelden", "task": "3-mal anmelden", "coins": 30},
                {"name": "Ausrüstung erhalten", "task": "1 einzigartiges Ausrüstungsteil erhalten", "coins": 20},
                {"name": "Schriftrolle benutzen", "task": "5 Schriftrollen benutzen", "coins": 20},
                {"name": "Dimensionale Invasion", "task": "1-mal an der Dimensionalen Invasion teilnehmen", "coins": 20},
                {"name": "Shugofesta", "task": "1-mal an der Shugofesta teilnehmen", "coins": 20},
            ],
        },
        {
            "title": "🛍️ Halloween-Eventshop",
            "description": "Beim Event-Münzhändler: Elyos – Verteron (Basis der Legion der Morgenröte / Zumionstätte); Asmodier – Altgard (Exulantendorf / Nornirkonvent). Preise in Halloween-Kürbismünzen (Event); Menge je Kauf: 1.",
            "entries": [
                {"name": "Halloween-Spezialtruhe", "price": 250, "limit": "1 pro Server", "level": 10},
                {"name": "Odenergie (Gebunden)", "price": 10, "limit": "4 pro Server/Woche", "level": 45},
                {"name": "Abyss-Rissstein: Untere Ebene (Gebunden)", "price": 30, "limit": "2 pro Server/Woche", "level": 45},
                {"name": "Skin-Truhe (10x) (Gebunden)", "price": 15, "limit": "5 pro Server/Woche", "level": 10},
                {"name": "Geiststein der Wiederbelebung (Gebunden)", "price": 2, "limit": "10 pro Server/Woche", "level": 10},
                {"name": "Sofortabschluss-Ticket: Täglicher Dungeon (Gebunden)", "price": 3, "limit": "7 pro Server/Woche", "level": 10},
                {"name": "Herausforderungsticket: Albtraum-Dungeon (Gebunden)", "price": 7, "limit": "3 pro Server/Woche", "level": 10},
                {"name": "Shugofesta-Schlüssel (Gebunden)", "price": 7, "limit": "3 pro Server/Woche", "level": 10},
                {"name": "Lebenskristall (Gebunden)", "price": 2, "limit": "20 pro Charakter", "level": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "price": 2, "limit": "10 pro Charakter", "level": 10},
                {"name": "Halloween-Keks (Gebunden)", "price": 2, "limit": "10 pro Charakter", "level": 10},
                {"name": "Hochwertiger Siegelstein (Gebunden)", "price": 1, "limit": "Keine angegebene Begrenzung", "level": 10},
            ],
        },
        {
            "title": "🎁 Halloween-Spezialtruhe",
            "entries": [
                {"name": "Gruseliges Skelett (Skin: Brustpanzer) (Gebunden)", "quantity": 1},
                {"name": "Pet-Seelenkristall", "quantity": 10000},
            ],
        },
        {
            "title": "🍬 Verbrauchsgegenstände",
            "entries": [
                {
                    "name": "Halloween-Süßigkeiten (Gebunden)",
                    "duration": "5 Minuten",
                    "effects": [
                        "Angriffskraft +25",
                        "Verteidigung +250",
                        "Max. SP +300",
                        "Natürliche SP-Erholung +40 %",
                    ],
                },
                {
                    "name": "Halloween-Keks (Gebunden)",
                    "duration": "5 Minuten",
                    "effects": [
                        "Max. LP +500",
                        "Max. MP +250",
                        "Max. SP +300",
                        "Natürliche SP-Erholung +40 %",
                    ],
                },
            ],
        },
        {
            "title": "🔑 Süßigkeitenschlüssel – Umwandlung",
            "description": "Süßigkeitenschlüssel-Fragmente (Event) erhältst du bei Expeditions- und Transzendenz-Zusammenstößen. Erfolgsrate aller Umwandlungen: 100 %. Rote, gelbe und blaue Schlüssel: jeweils einmal pro Woche pro Server.",
            "entries": [
                {"name": "Roter Süßigkeitenschlüssel (Event)", "quantity": 1, "fragments": 60},
                {"name": "Gelber Süßigkeitenschlüssel (Event)", "quantity": 1, "fragments": 60},
                {"name": "Blauer Süßigkeitenschlüssel (Event)", "quantity": 1, "fragments": 60},
                {"name": "Hochwertiger Siegelstein (Gebunden)", "quantity": 10, "fragments": 1},
            ],
        },
        {
            "title": "🔴 Rote Süßigkeiten – Inhalt",
            "entries": [
                {"name": "Pet-Truhe des Wachstums (Gebunden)", "quantity": 20},
                {"name": "Rolle der Kampf-Verstärkung (Gebunden)", "quantity": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "quantity": 5},
                {"name": "Halloween-Keks (Gebunden)", "quantity": 5},
            ],
        },
        {
            "title": "🟡 Gelbe Süßigkeiten – Inhalt",
            "entries": [
                {"name": "Abysspunkte", "quantity": 10000},
                {"name": "Lebenskristall (Gebunden)", "quantity": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "quantity": 5},
                {"name": "Halloween-Keks (Gebunden)", "quantity": 5},
            ],
        },
        {
            "title": "🔵 Blaue Süßigkeiten – Inhalt",
            "entries": [
                {"name": "Odenergie (Gebunden)", "quantity": 4},
                {"name": "Geiststein der Wiederbelebung (Gebunden)", "quantity": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "quantity": 5},
                {"name": "Halloween-Keks (Gebunden)", "quantity": 5},
            ],
        },
    ],
}


WIDTH = 1200
HEIGHT = 180


def status(now=None):
    tz = ZoneInfo(EVENT["timezone"])
    now = now.astimezone(tz) if now is not None else datetime.now(tz)

    start = datetime.fromisoformat(EVENT["start"]).astimezone(tz)
    end = datetime.fromisoformat(EVENT["end"]).astimezone(tz)

    if now < start:
        return "upcoming"
    if now < end:
        return "active"
    return "finished"


def font(size, bold=True):
    paths = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
        if bold else
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    )

    for path in paths:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)

    raise RuntimeError("Keine geeignete Schriftart gefunden.")


def load_background():
    path = Path(__file__).resolve().parent / "halloween.png"

    if not path.is_file():
        raise FileNotFoundError(f"Originalbanner fehlt: {path}")

    with Image.open(path) as original:
        if original.size != (WIDTH, HEIGHT):
            raise ValueError(
                f"Falsches Originalformat: {original.size}. "
                f"Erwartet: {WIDTH} × {HEIGHT}. "
                "Das Bild wird ausdrücklich nicht zugeschnitten."
            )

        return original.convert("RGBA")


def draw_halloween_text(base, text, face, center_y, spacing=0,
                        subtitle=False, seed=20261030):
    w, h = base.size
    draw = ImageDraw.Draw(base)

    widths = [draw.textlength(c, font=face) for c in text]
    text_width = sum(widths) + spacing * max(0, len(text) - 1)

    bbox = draw.textbbox((0, 0), text, font=face)
    visible_height = bbox[3] - bbox[1]

    x = (w - text_width) / 2
    y = center_y - visible_height / 2 - bbox[1]

    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)

    for index, character in enumerate(text):
        md.text((round(x), round(y)), character, font=face, fill=255)
        x += widths[index] + spacing

    bounds = mask.getbbox()
    if bounds is None:
        return

    # Dunkler Schatten für plastische, unheimliche Schrift.
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_mask = mask.filter(ImageFilter.GaussianBlur(5 if subtitle else 9))
    shadow_layer = Image.new("RGBA", (w, h), (8, 0, 0, 0))
    shadow_layer.putalpha(
        shadow_mask.point(lambda a: int(a * (0.75 if not subtitle else 0.55)))
    )
    shadow.alpha_composite(shadow_layer, (0, 0))
    base.alpha_composite(shadow)

    # Kräftiger, orange-roter Feuerschein.
    for radius, color, strength in (
        (14, (255, 40, 0), 0.35),
        (7, (255, 85, 0), 0.58),
        (3, (255, 165, 20), 0.45),
    ):
        glow_mask = mask.filter(ImageFilter.GaussianBlur(radius))
        glow = Image.new("RGBA", (w, h), (*color, 0))
        glow.putalpha(
            glow_mask.point(
                lambda a, s=strength: int(a * (s * 0.6 if subtitle else s))
            )
        )
        base.alpha_composite(glow)

    # Verlauf: glühende Oberkante, tieforange Unterkante.
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gp = gradient.load()

    top, bottom = bounds[1], bounds[3]
    span = max(1, bottom - top)

    for py in range(top, bottom):
        t = (py - top) / span

        if subtitle:
            color = (
                255,
                int(207 - 75 * t),
                int(98 - 80 * t),
                255,
            )
        elif t < 0.35:
            f = t / 0.35
            color = (
                255,
                int(232 - 100 * f),
                int(98 - 80 * f),
                255,
            )
        else:
            f = (t - 0.35) / 0.65
            color = (
                int(255 - 32 * f),
                int(132 - 92 * f),
                int(18 - 18 * f),
                255,
            )

        for px in range(bounds[0], bounds[2]):
            gp[px, py] = color

    gradient.putalpha(mask)
    base.alpha_composite(gradient)

    if subtitle:
        return

    # Risse ausschließlich innerhalb der Buchstaben.
    rng = random.Random(seed)
    crack_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(crack_layer)

    for _ in range(65):
        cx = rng.randrange(bounds[0], bounds[2])
        cy = rng.randrange(bounds[1], bounds[3])

        if mask.getpixel((cx, cy)) < 200:
            continue

        points = [(cx, cy)]

        for _ in range(rng.randint(2, 4)):
            cx += rng.randint(-8, 8)
            cy += rng.randint(3, 8)
            points.append((cx, cy))

        cd.line(
            points,
            fill=(18, 3, 1, rng.randint(175, 235)),
            width=rng.choice((1, 2, 2, 3)),
        )

    clipped_alpha = Image.composite(
        crack_layer.getchannel("A"),
        Image.new("L", (w, h), 0),
        mask,
    )
    crack_layer.putalpha(clipped_alpha)
    base.alpha_composite(crack_layer)


def banner(current):
    """
    Fertiges Halloween-Banner: exakt 1200 × 180 Pixel.
    Das Original wird weder skaliert noch zugeschnitten.
    """

    labels = {
        "upcoming": "BALD VERFÜGBAR",
        "active": "GESTARTET",
        "finished": "BEENDET",
    }

    if current not in labels:
        raise ValueError(f"Unbekannter Eventstatus: {current}")

    base = load_background()

    # Nur die Textmitte leicht abdunkeln.
    # Die Motive links und rechts bleiben unverändert.
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    alpha = Image.new("L", (WIDTH, HEIGHT), 0)
    ap = alpha.load()

    for x in range(WIDTH):
        distance = abs(x - WIDTH / 2) / 310
        strength = max(0, 1 - distance)
        value = int(95 * strength ** 1.3)

        for y in range(HEIGHT):
            ap[x, y] = value

    overlay.putalpha(alpha.filter(ImageFilter.GaussianBlur(12)))
    base = Image.alpha_composite(base, overlay)

    title = "HALLOWEEN"
    subtitle = f'{EVENT["date_label"]} · {labels[current]}'

    draw = ImageDraw.Draw(base)

    # Groß, aber auf die freie Bildmitte begrenzt.
    title_size = 78
    title_spacing = 3

    while title_size >= 35:
        title_font = font(title_size)
        title_width = (
            draw.textlength(title, font=title_font)
            + title_spacing * (len(title) - 1)
        )
        if title_width <= 650:
            break
        title_size -= 1

    subtitle_size = 25

    while subtitle_size >= 14:
        subtitle_font = font(subtitle_size)
        if draw.textlength(subtitle, font=subtitle_font) <= 610:
            break
        subtitle_size -= 1

    draw_halloween_text(
        base,
        title,
        title_font,
        center_y=78,
        spacing=title_spacing,
        subtitle=False,
    )

    draw_halloween_text(
        base,
        subtitle,
        subtitle_font,
        center_y=137,
        subtitle=True,
    )

    output = io.BytesIO()
    result = base.convert("RGB")

    if result.size != (1200, 180):
        raise RuntimeError("Bannerformat stimmt nicht.")

    result.save(output, format="PNG", optimize=True)
    return output.getvalue()


def entry_line(entry):
    if "days" in entry:
        return (
            f'• **Tag {entry["days"]}** — '
            f'**{entry["coins_per_day"]} Münzen/Tag**'
        )

    name = entry.get("name", "")

    if "task" in entry:
        return (
            f'• {name}: {entry["task"]} '
            f'→ **{entry["coins"]} Münzen**'
        )

    if "price" in entry:
        return (
            f'• **{name}** — **{entry["price"]} Münzen**\n'
            f'  ↳ {entry["limit"]} · ab Stufe {entry["level"]}'
        )

    if "fragments" in entry:
        return (
            f'• {name} ×{entry["quantity"]} — '
            f'**{entry["fragments"]} Fragmente**'
        )

    if "effects" in entry:
        return (
            f'• **{name}** ({entry["duration"]})\n'
            f'  ↳ {" · ".join(entry["effects"])}'
        )

    quantity = f'{entry.get("quantity", 1):,}'.replace(",", ".")
    return f'• {name} — **×{quantity}**'


def detail_embeds():
    embeds = []

    for section in EVENT["sections"]:
        lines = []

        if section.get("description"):
            lines.extend((section["description"], ""))

        lines.extend(
            entry_line(entry)
            for entry in section["entries"]
        )

        description = "\n".join(lines)

        if len(description) > 4096:
            raise ValueError(
                f'Eventabschnitt zu lang: {section["title"]}'
            )

        embeds.append({
            "title": section["title"],
            "description": description,
            "color": 0xFF7100,
        })

    return embeds


def payload(current):
    """
    Kompatibilität zur bisherigen Eventstruktur.
    Die zentrale events.py verwaltet den öffentlichen Button.
    """

    source = EVENT["source_url"]

    if not source.startswith("https://"):
        raise ValueError("Gültige HTTPS-Quellen-URL fehlt.")

    filename = f'{EVENT["id"]}_banner.png'

    labels = {
        "upcoming": "Bald verfügbar",
        "active": "Aktiv",
        "finished": "Beendet",
    }

    return {
        "embeds": [
            {
                "title": "🔗 Eventankündigung & Belohnungen",
                "url": source,
                "description": (
                    f'**Zeitraum:** {EVENT["date_label"]}\n'
                    f'**Status:** {labels[current]}\n\n'
                    "Alle Halloween-Details findest du "
                    "über den Button unter dem Banner."
                ),
                "color": 0xFF7100,
                "image": {
                    "url": f"attachment://{filename}"
                },
                "footer": {
                    "text": EVENT["id"]
                },
            }
        ],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 1,
                        "label": "🎃 Eventdetails anzeigen",
                        "custom_id": "event:details:halloween_2026",
                    }
                ],
            }
        ],
        "allowed_mentions": {"parse": []},
    }


if __name__ == "__main__":
    print(f'{EVENT["name"]}: {status()}')
    print(f"Bannerformat: {WIDTH} × {HEIGHT}")
