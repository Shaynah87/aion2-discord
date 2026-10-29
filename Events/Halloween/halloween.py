
"""
Nyerk24 · Halloween 2026

Eventdaten, Banner und Discord-Inhalte.

Bannerformat: 1200 x 220 Pixel
Originalmotiv: halloween.png

Die zentrale Events/events.py übernimmt die Veröffentlichung.
Die privaten Eventdetails werden über den Cloudflare-Worker
nyerk24-events angezeigt.
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
    "source_url": (
        "https://aion2.plaync.com/de-de/eventon/board/"
        "event_notice/view?articleId=6acf216807b77e214688a773"
    ),
    "sections": [
        {
            "title": "🎃 Süßes oder Saures – Anwesenheit",
            "description": (
                "Tägliche Anmeldung über das Eventmenü. "
                "Belohnung: Halloween-Kürbismünzen (Event)."
            ),
            "entries": [
                {"days": "1–6", "coins_per_day": 35},
                {"days": "7", "coins_per_day": 100},
                {"days": "8–13", "coins_per_day": 35},
                {"days": "14", "coins_per_day": 100},
            ],
        },
        {
            "title": "⚔️ Saisonmissionen – Event",
            "description": (
                "Im Spiel unter [Saisonmission] > [Event]. "
                "Einmal pro Woche pro Server. "
                "Belohnungen jeweils in Halloween-Kürbismünzen (Event)."
            ),
            "entries": [
                {
                    "name": "Abyssus",
                    "task": "10 Monster im Abyssus jagen",
                    "coins": 25,
                },
                {
                    "name": "Transzendenz",
                    "task": "1-mal den Transzendenz-Dungeon abschließen",
                    "coins": 25,
                },
                {
                    "name": "Expedition",
                    "task": "1-mal die Expeditions-Eroberung abschließen",
                    "coins": 25,
                },
                {
                    "name": "Aszensusritus",
                    "task": "1-mal den Aszensusritus abschließen",
                    "coins": 25,
                },
                {
                    "name": "Albtraum",
                    "task": "1-mal abschließen (beliebige Stufe)",
                    "coins": 25,
                },
                {
                    "name": "Anmelden",
                    "task": "3-mal anmelden",
                    "coins": 30,
                },
                {
                    "name": "Ausrüstung erhalten",
                    "task": "1 einzigartiges Ausrüstungsteil erhalten",
                    "coins": 20,
                },
                {
                    "name": "Schriftrolle benutzen",
                    "task": "5 Schriftrollen benutzen",
                    "coins": 20,
                },
                {
                    "name": "Dimensionale Invasion",
                    "task": "1-mal an der Dimensionalen Invasion teilnehmen",
                    "coins": 20,
                },
                {
                    "name": "Shugofesta",
                    "task": "1-mal an der Shugofesta teilnehmen",
                    "coins": 20,
                },
            ],
        },
        {
            "title": "🛍️ Halloween-Eventshop",
            "description": (
                "Beim Event-Münzhändler: "
                "Elyos – Verteron (Basis der Legion der Morgenröte / "
                "Zumionstätte); "
                "Asmodier – Altgard (Exulantendorf / Nornirkonvent). "
                "Preise in Halloween-Kürbismünzen (Event); "
                "Menge je Kauf: 1."
            ),
            "entries": [
                {
                    "name": "Halloween-Spezialtruhe",
                    "price": 250,
                    "limit": "1 pro Server",
                    "level": 10,
                },
                {
                    "name": "Odenergie (Gebunden)",
                    "price": 10,
                    "limit": "4 pro Server/Woche",
                    "level": 45,
                },
                {
                    "name": "Abyss-Rissstein: Untere Ebene (Gebunden)",
                    "price": 30,
                    "limit": "2 pro Server/Woche",
                    "level": 45,
                },
                {
                    "name": "Skin-Truhe (10x) (Gebunden)",
                    "price": 15,
                    "limit": "5 pro Server/Woche",
                    "level": 10,
                },
                {
                    "name": "Geiststein der Wiederbelebung (Gebunden)",
                    "price": 2,
                    "limit": "10 pro Server/Woche",
                    "level": 10,
                },
                {
                    "name": (
                        "Sofortabschluss-Ticket: "
                        "Täglicher Dungeon (Gebunden)"
                    ),
                    "price": 3,
                    "limit": "7 pro Server/Woche",
                    "level": 10,
                },
                {
                    "name": (
                        "Herausforderungsticket: "
                        "Albtraum-Dungeon (Gebunden)"
                    ),
                    "price": 7,
                    "limit": "3 pro Server/Woche",
                    "level": 10,
                },
                {
                    "name": "Shugofesta-Schlüssel (Gebunden)",
                    "price": 7,
                    "limit": "3 pro Server/Woche",
                    "level": 10,
                },
                {
                    "name": "Lebenskristall (Gebunden)",
                    "price": 2,
                    "limit": "20 pro Charakter",
                    "level": 10,
                },
                {
                    "name": "Halloween-Süßigkeiten (Gebunden)",
                    "price": 2,
                    "limit": "10 pro Charakter",
                    "level": 10,
                },
                {
                    "name": "Halloween-Keks (Gebunden)",
                    "price": 2,
                    "limit": "10 pro Charakter",
                    "level": 10,
                },
                {
                    "name": "Hochwertiger Siegelstein (Gebunden)",
                    "price": 1,
                    "limit": "Keine angegebene Begrenzung",
                    "level": 10,
                },
            ],
        },
        {
            "title": "🎁 Halloween-Spezialtruhe",
            "entries": [
                {
                    "name": (
                        "Gruseliges Skelett "
                        "(Skin: Brustpanzer) (Gebunden)"
                    ),
                    "quantity": 1,
                },
                {
                    "name": "Pet-Seelenkristall",
                    "quantity": 10000,
                },
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
            "description": (
                "Süßigkeitenschlüssel-Fragmente (Event) erhältst "
                "du bei Expeditions- und Transzendenz-Zusammenstößen. "
                "Erfolgsrate aller Umwandlungen: 100 %. "
                "Rote, gelbe und blaue Schlüssel: "
                "jeweils einmal pro Woche pro Server."
            ),
            "entries": [
                {
                    "name": "Roter Süßigkeitenschlüssel (Event)",
                    "quantity": 1,
                    "fragments": 60,
                },
                {
                    "name": "Gelber Süßigkeitenschlüssel (Event)",
                    "quantity": 1,
                    "fragments": 60,
                },
                {
                    "name": "Blauer Süßigkeitenschlüssel (Event)",
                    "quantity": 1,
                    "fragments": 60,
                },
                {
                    "name": "Hochwertiger Siegelstein (Gebunden)",
                    "quantity": 10,
                    "fragments": 1,
                },
            ],
        },
        {
            "title": "🔴 Rote Süßigkeiten – Inhalt",
            "entries": [
                {
                    "name": "Pet-Truhe des Wachstums (Gebunden)",
                    "quantity": 20,
                },
                {
                    "name": "Rolle der Kampf-Verstärkung (Gebunden)",
                    "quantity": 10,
                },
                {
                    "name": "Halloween-Süßigkeiten (Gebunden)",
                    "quantity": 5,
                },
                {
                    "name": "Halloween-Keks (Gebunden)",
                    "quantity": 5,
                },
            ],
        },
        {
            "title": "🟡 Gelbe Süßigkeiten – Inhalt",
            "entries": [
                {
                    "name": "Abysspunkte",
                    "quantity": 10000,
                },
                {
                    "name": "Lebenskristall (Gebunden)",
                    "quantity": 10,
                },
                {
                    "name": "Halloween-Süßigkeiten (Gebunden)",
                    "quantity": 5,
                },
                {
                    "name": "Halloween-Keks (Gebunden)",
                    "quantity": 5,
                },
            ],
        },
        {
            "title": "🔵 Blaue Süßigkeiten – Inhalt",
            "entries": [
                {
                    "name": "Odenergie (Gebunden)",
                    "quantity": 4,
                },
                {
                    "name": "Geiststein der Wiederbelebung (Gebunden)",
                    "quantity": 10,
                },
                {
                    "name": "Halloween-Süßigkeiten (Gebunden)",
                    "quantity": 5,
                },
                {
                    "name": "Halloween-Keks (Gebunden)",
                    "quantity": 5,
                },
            ],
        },
    ],
}


BANNER_WIDTH = 1200
BANNER_HEIGHT = 220


def status(now=None):
    tz = ZoneInfo(EVENT["timezone"])

    if now is None:
        now = datetime.now(tz)
    else:
        now = now.astimezone(tz)

    start = datetime.fromisoformat(
        EVENT["start"]
    ).astimezone(tz)

    end = datetime.fromisoformat(
        EVENT["end"]
    ).astimezone(tz)

    if now < start:
        return "upcoming"

    if now < end:
        return "active"

    return "finished"


def font(size, bold=True):
    if bold:
        choices = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        choices = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in choices:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def fit_font(draw, text, initial_size, max_width):
    size = initial_size

    while size >= 12:
        candidate = font(size)
        width = draw.textlength(text, font=candidate)

        if width <= max_width:
            return candidate

        size -= 1

    return font(12)


def prepare_background():
    source_path = (
        Path(__file__).resolve().parent
        / "halloween.png"
    )

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Halloween-Banner fehlt: {source_path}"
        )

    with Image.open(source_path) as image:
        source = image.convert("RGB")

    width = BANNER_WIDTH
    height = BANNER_HEIGHT

    # Proportional skalieren, niemals verzerren.
    factor = max(
        width / source.width,
        height / source.height
    )

    resized_width = round(source.width * factor)
    resized_height = round(source.height * factor)

    source = source.resize(
        (resized_width, resized_height),
        Image.Resampling.LANCZOS
    )

    left = (resized_width - width) // 2
    top = (resized_height - height) // 2

    background = source.crop(
        (
            left,
            top,
            left + width,
            top + height
        )
    ).convert("RGBA")

    return background


def add_center_shading(base):
    width, height = base.size

    shade = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    alpha = Image.new(
        "L",
        (width, height),
        0
    )

    pixels = alpha.load()

    for x in range(width):
        distance = abs(
            x - width / 2
        ) / (width * 0.43)

        strength = max(
            0.0,
            1.0 - distance
        )

        value = int(
            125 * (strength ** 0.65)
        )

        for y in range(height):
            pixels[x, y] = value

    shade.putalpha(
        alpha.filter(
            ImageFilter.GaussianBlur(18)
        )
    )

    return Image.alpha_composite(
        base,
        shade
    )


def ember_text(
    base,
    value,
    face,
    y,
    seed,
    subtitle=False,
    spacing=0
):
    width, height = base.size

    draw = ImageDraw.Draw(base)

    bounds = draw.textbbox(
        (0, 0),
        value,
        font=face
    )

    text_width = sum(
        draw.textlength(
            character,
            font=face
        )
        for character in value
    )

    text_width += (
        max(0, len(value) - 1)
        * spacing
    )

    x = (width - text_width) / 2

    text_y = int(
        y - bounds[1]
    )

    mask = Image.new(
        "L",
        (width, height),
        0
    )

    mask_draw = ImageDraw.Draw(mask)

    for index, character in enumerate(value):
        mask_draw.text(
            (x, text_y),
            character,
            font=face,
            fill=255
        )

        x += draw.textlength(
            character,
            font=face
        )

        if index < len(value) - 1:
            x += spacing

    bbox = mask.getbbox()

    if not bbox:
        return

    # Dezenter orangefarbener Lichtschein.
    glow = Image.new(
        "RGBA",
        (width, height),
        (255, 85, 0, 0)
    )

    blur_radius = (
        4 if subtitle else 8
    )

    glow_alpha = mask.filter(
        ImageFilter.GaussianBlur(
            blur_radius
        )
    )

    intensity = (
        0.25 if subtitle else 0.50
    )

    glow.putalpha(
        glow_alpha.point(
            lambda alpha: int(
                alpha * intensity
            )
        )
    )

    base.alpha_composite(glow)

    # Orangefarbener Farbverlauf innerhalb der Schrift.
    fill_layer = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    fill_pixels = fill_layer.load()

    top = bbox[1]
    bottom = max(
        bbox[3],
        top + 1
    )

    for py in range(top, bottom):
        t = (
            (py - top)
            / (bottom - top)
        )

        if subtitle:
            color = (
                255,
                int(186 - 65 * t),
                int(65 - 42 * t),
                255
            )

        elif t < 0.40:
            f = t / 0.40

            color = (
                255,
                int(179 - 83 * f),
                int(35 - 28 * f),
                255
            )

        else:
            f = (
                (t - 0.40)
                / 0.60
            )

            color = (
                int(255 - 28 * f),
                int(96 - 57 * f),
                int(7 - 7 * f),
                255
            )

        for px in range(
            bbox[0],
            bbox[2]
        ):
            fill_pixels[px, py] = color

    fill_layer.putalpha(mask)

    base.alpha_composite(
        fill_layer
    )

    # Kleine Risse in der großen Halloween-Schrift.
    if not subtitle:
        rng = random.Random(seed)

        crack_layer = Image.new(
            "RGBA",
            (width, height),
            (0, 0, 0, 0)
        )

        cracks = ImageDraw.Draw(
            crack_layer
        )

        for _ in range(24):
            cx = rng.randint(
                bbox[0],
                bbox[2] - 1
            )

            cy = rng.randint(
                bbox[1],
                bbox[3] - 1
            )

            length = rng.randint(
                5,
                14
            )

            points = [(cx, cy)]

            for _step in range(3):
                cx += rng.randint(
                    -5,
                    5
                )

                cy += (
                    max(1, length // 3)
                    + rng.randint(-2, 2)
                )

                points.append(
                    (cx, cy)
                )

            cracks.line(
                points,
                fill=(
                    22,
                    5,
                    3,
                    rng.randint(145, 215)
                ),
                width=rng.choice(
                    (1, 1, 2)
                )
            )

        crack_alpha = Image.composite(
            crack_layer.getchannel("A"),
            Image.new(
                "L",
                (width, height),
                0
            ),
            mask
        )

        crack_layer.putalpha(
            crack_alpha
        )

        base.alpha_composite(
            crack_layer
        )


def banner(current):
    """
    Erzeugt das fertige Halloween-Banner.

    Exakte Ausgabe: 1200 x 220 Pixel.
    """

    width = BANNER_WIDTH
    height = BANNER_HEIGHT

    base = prepare_background()

    base = add_center_shading(
        base
    )

    labels = {
        "upcoming": "BALD VERFÜGBAR",
        "active": "GESTARTET",
        "finished": "BEENDET"
    }

    if current not in labels:
        raise ValueError(
            f"Unbekannter Eventstatus: {current}"
        )

    title = EVENT["name"].upper()

    subtitle = (
        f'{EVENT["date_label"]} '
        f'· {labels[current]}'
    )

    draw = ImageDraw.Draw(base)

    title_font = fit_font(
        draw,
        title,
        initial_size=61,
        max_width=width * 0.52
    )

    subtitle_font = fit_font(
        draw,
        subtitle,
        initial_size=28,
        max_width=width * 0.65
    )

    title_bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    subtitle_bbox = draw.textbbox(
        (0, 0),
        subtitle,
        font=subtitle_font
    )

    title_height = (
        title_bbox[3]
        - title_bbox[1]
    )

    subtitle_height = (
        subtitle_bbox[3]
        - subtitle_bbox[1]
    )

    gap = 15

    total_height = (
        title_height
        + gap
        + subtitle_height
    )

    top_y = (
        height - total_height
    ) / 2

    ember_text(
        base,
        title,
        title_font,
        top_y,
        seed=20261014,
        subtitle=False,
        spacing=4
    )

    ember_text(
        base,
        subtitle,
        subtitle_font,
        top_y + title_height + gap,
        seed=20261104,
        subtitle=True
    )

    output = io.BytesIO()

    final_image = base.convert(
        "RGB"
    )

    if final_image.size != (
        1200,
        220
    ):
        raise RuntimeError(
            "Falsches Halloween-Bannerformat."
        )

    final_image.save(
        output,
        format="PNG",
        optimize=True
    )

    return output.getvalue()


def entry_line(entry):
    if "days" in entry:
        return (
            f'• **Tag {entry["days"]}**'
            f' — **{entry["coins_per_day"]} Münzen/Tag**'
        )

    name = entry.get(
        "name",
        ""
    )

    if "task" in entry:
        return (
            f'• {name}: {entry["task"]}'
            f' → **{entry["coins"]} Münzen**'
        )

    if "price" in entry:
        return (
            f'• **{name}**'
            f' — **{entry["price"]} Münzen**\n'
            f'  ↳ {entry["limit"]}'
            f' · ab Stufe {entry["level"]}'
        )

    if "fragments" in entry:
        return (
            f'• {name} ×{entry["quantity"]}'
            f' — **{entry["fragments"]} Fragmente**'
        )

    if "effects" in entry:
        return (
            f'• **{name}**'
            f' ({entry["duration"]})\n'
            f'  ↳ {" · ".join(entry["effects"])}'
        )

    quantity = (
        f'{entry.get("quantity", 1):,}'
        .replace(",", ".")
    )

    return (
        f'• {name}'
        f' — **×{quantity}**'
    )


def detail_embeds():
    """
    Vollständige Detail-Embeds.

    Diese Funktion bleibt zur Datenkompatibilität
    erhalten. Die öffentliche events.py verwendet
    sie nicht mehr.
    """

    embeds = []

    for section in EVENT["sections"]:
        lines = []

        if section.get("description"):
            lines.extend(
                (
                    section["description"],
                    ""
                )
            )

        lines.extend(
            entry_line(entry)
            for entry in section["entries"]
        )

        description = "\n".join(
            lines
        )

        if len(description) > 4096:
            raise ValueError(
                "Eventabschnitt zu lang: "
                f'{section["title"]}'
            )

        embeds.append({
            "title": section["title"],
            "description": description,
            "color": 0xFF7100
        })

    return embeds


def payload(current):
    """
    Kompatible öffentliche Eventdarstellung.

    Die zentrale events.py erstellt ihre eigene
    öffentliche Nachricht mit interaktivem Button.
    """

    source = EVENT["source_url"]

    if not source.startswith(
        "https://"
    ):
        raise ValueError(
            "Gültige HTTPS-Quellen-URL fehlt."
        )

    filename = (
        f'{EVENT["id"]}_banner.png'
    )

    status_labels = {
        "upcoming": "Bald verfügbar",
        "active": "Aktiv",
        "finished": "Beendet"
    }

    status_label = status_labels.get(
        current,
        "Unbekannt"
    )

    return {
        "embeds": [
            {
                "title": (
                    "🔗 Eventankündigung "
                    "& Belohnungen ansehen"
                ),
                "url": source,
                "description": (
                    f'**Zeitraum:** {EVENT["date_label"]}\n'
                    f'**Status:** {status_label}\n\n'
                    "Alle Halloween-Details findest du "
                    "über den Button unter dem Banner."
                ),
                "color": 0xFF7100,
                "image": {
                    "url": (
                        f"attachment://{filename}"
                    )
                },
                "footer": {
                    "text": EVENT["id"]
                }
            }
        ],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 1,
                        "label": (
                            "🎃 Eventdetails anzeigen"
                        ),
                        "custom_id": (
                            "event:details:halloween_2026"
                        )
                    }
                ]
            }
        ],
        "allowed_mentions": {
            "parse": []
        }
    }


if __name__ == "__main__":
    print(
        f'{EVENT["name"]}: {status()}'
    )

    print(
        "Bannerformat: "
        f"{BANNER_WIDTH} × {BANNER_HEIGHT}"
    )
