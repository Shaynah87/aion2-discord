
"""
Nyerk24 · Halloween 2026

Der Halloween-Schriftzug ist fest im PNG integriert.
Python ergänzt ausschließlich Datum und Status.

Banner: 1200 x 180 Pixel
Datum: 30 px BOLD
Status: 30 px BOLD

Alle neun Eventbereiche bleiben erhalten.
"""

import io
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


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

SUBTITLE_SIZE = 30
SUBTITLE_Y = 145

DATE_COLOR = "#FFD28A"
STARTED_COLOR = "#83D9AC"
UPCOMING_COLOR = "#F29B72"
FINISHED_COLOR = "#AEB5C1"


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


def font(size):
    paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
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
                f"Erwartet: {WIDTH} x {HEIGHT}. "
                "Das Bild wird nicht skaliert oder zugeschnitten."
            )

        return original.convert("RGBA")


def draw_subtitle(base, current):
    """
    Datum und Status gemeinsam auf einer Zeile.
    Beide mit derselben Schrift und Größe.
    """

    labels = {
        "upcoming": ("BALD VERFÜGBAR", UPCOMING_COLOR),
        "active": ("GESTARTET", STARTED_COLOR),
        "finished": ("BEENDET", FINISHED_COLOR),
    }

    if current not in labels:
        raise ValueError(f"Unbekannter Eventstatus: {current}")

    status_text, status_color = labels[current]

    date_text = EVENT["date_label"]
    separator = " · "

    face = font(SUBTITLE_SIZE)
    draw = ImageDraw.Draw(base)

    date_width = draw.textlength(date_text, font=face)
    separator_width = draw.textlength(separator, font=face)
    status_width = draw.textlength(status_text, font=face)

    total_width = (
        date_width
        + separator_width
        + status_width
    )

    x = (WIDTH - total_width) / 2

    text_style = {
        "font": face,
        "anchor": "mm",
        "stroke_width": 2,
        "stroke_fill": "#170600",
    }

    # Datum und Status verwenden dieselbe
    # Schriftgröße und dieselbe vertikale Position.

    draw.text(
        (x + date_width / 2, SUBTITLE_Y),
        date_text,
        fill=DATE_COLOR,
        **text_style,
    )

    x += date_width

    draw.text(
        (x + separator_width / 2, SUBTITLE_Y),
        separator,
        fill=DATE_COLOR,
        **text_style,
    )

    x += separator_width

    draw.text(
        (x + status_width / 2, SUBTITLE_Y),
        status_text,
        fill=status_color,
        **text_style,
    )


def banner(current):
    """
    Verwendet das fertige Halloween-PNG
    und ergänzt nur Datum und Status.
    """

    base = load_background()

    draw_subtitle(base, current)

    result = base.convert("RGB")

    if result.size != (WIDTH, HEIGHT):
        raise RuntimeError("Bannerformat stimmt nicht.")

    output = io.BytesIO()

    result.save(
        output,
        format="PNG",
        optimize=True,
    )

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
    Die zentrale events.py verwaltet
    den öffentlichen Button.
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
    print(f"Bannerformat: {WIDTH} x {HEIGHT}")
