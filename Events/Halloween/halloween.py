
"""Halloween 2026: feste Daten, Bannerdesign und Discord-Darstellung.

Änderungen am Event erfolgen hier; keine automatische Inhaltsbeschaffung.
Die zentrale events.py kümmert sich ausschließlich um das Veröffentlichen.
"""
import io
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from datetime import datetime
from zoneinfo import ZoneInfo

EVENT = {
    "id": "halloween_2026",
    "name": "Halloween",
    "timezone": "Europe/Berlin",
    "start": "2026-10-14T00:00:00+02:00",  # Datum bekannt, genaue Wartungszeit nicht angegeben
    "end": "2026-11-04T09:00:00+01:00",
    "date_label": "14.10. – 04.11.2026",
    "image": "Events/Halloween/halloween.png",
    "currency": "Halloween-Kürbismünze (Event)",
    "source_url": "https://patchbot.io/games/aion-2/articles/1777-notice-patch-notes-oct-13-pdt-oct-14-cest",
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
                {"name": "Halloween-Süßigkeiten (Gebunden)", "duration": "5 Minuten", "effects": ["Angriffskraft +25", "Verteidigung +250", "Max. SP +300", "Natürliche SP-Erholung +40 %"]},
                {"name": "Halloween-Keks (Gebunden)", "duration": "5 Minuten", "effects": ["Max. LP +500", "Max. MP +250", "Max. SP +300", "Natürliche SP-Erholung +40 %"]},
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


def status(now=None):
    """Gibt 'upcoming', 'active' oder 'finished' zurück."""
    tz = ZoneInfo(EVENT["timezone"])
    now = now.astimezone(tz) if now is not None else datetime.now(tz)
    start = datetime.fromisoformat(EVENT["start"]).astimezone(tz)
    end = datetime.fromisoformat(EVENT["end"]).astimezone(tz)
    if now < start:
        return "upcoming"
    if now < end:
        return "active"
    return "finished"


if __name__ == "__main__":
    print(f'{EVENT["name"]}: {status()}')


# ===== HALLOWEEN-BANNER UND DISCORD-INHALT =====

def font(size, bold=True):
    choices = ([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ] if bold else [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ])
    for path in choices:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def banner(current):
    # Identisches Bannerformat bei allen Status, angelehnt an die Content-Header.
    width, height = 1200, 220
    source = Image.open(Path(__file__).resolve().parent / "halloween.png").convert("RGB")
    factor = max(width / source.width, height / source.height)
    source = source.resize((round(source.width * factor), round(source.height * factor)), Image.Resampling.LANCZOS)
    left = (source.width - width) // 2
    top = (source.height - height) // 2
    base = source.crop((left, top, left + width, top + height)).convert("RGBA")

    # Lesbarkeit: sanfter dunkler Mittelbereich, ohne die Randmotive zu verdecken.
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    alpha = Image.new("L", (width, height), 0)
    px = alpha.load()
    for x in range(width):
        strength = max(0.0, 1.0 - abs(x - width / 2) / (width * 0.43))
        value = int(135 * (strength ** 0.65))
        for y in range(height):
            px[x, y] = value
    overlay.putalpha(alpha.filter(ImageFilter.GaussianBlur(22)))
    base = Image.alpha_composite(base, overlay)

    labels = {"upcoming": "BALD VERFÜGBAR", "active": "GESTARTET", "finished": "BEENDET"}
    title = EVENT["name"].upper()
    subtitle = f'{EVENT["date_label"]} · {labels[current]}'
    draw = ImageDraw.Draw(base)
    title_font = font(49)
    subtitle_font = font(31)
    # Exakte Compact-Typografie aus Content/Launch/launch.py:
    # 1200 x 220, Titel 49 px, Status 31 px, Buchstabenabstand 5 px,
    # Abstand 18 px, vertikal anhand sichtbarer Glyphen zentriert.
    title_spacing = 5
    title_box = draw.textbbox((0, 0), title, font=title_font)
    sub_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    title_height = title_box[3] - title_box[1]
    sub_height = sub_box[3] - sub_box[1]
    gap = 18
    top_y = (height - (title_height + gap + sub_height)) / 2

    # Feuerorange mit eingebrannten dunklen Adern INNERHALB der Buchstaben.
    # Keine dicke schwarze Außenkontur: Die Textmaske begrenzt alle Strukturen.
    def ember_text(value, face, y, seed, subtitle=False, spacing=0):
        bounds = draw.textbbox((0, 0), value, font=face)
        total_width = sum(draw.textlength(ch, font=face) for ch in value) + max(0, len(value) - 1) * spacing
        x = (width - total_width) / 2
        text_y = int(y - bounds[1])
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        for index, ch in enumerate(value):
            mask_draw.text((x, text_y), ch, font=face, fill=255)
            x += draw.textlength(ch, font=face)
            if index < len(value) - 1:
                x += spacing
        bbox = mask.getbbox()
        if not bbox:
            return

        # Nur ein zurückhaltender Schein HINTER der Schrift.
        glow = Image.new("RGBA", (width, height), (255, 85, 0, 0))
        blurred = mask.filter(ImageFilter.GaussianBlur(11 if not subtitle else 6))
        glow.putalpha(blurred.point(lambda a: int(a * (0.53 if not subtitle else 0.25))))
        base.alpha_composite(glow)

        # Verlauf vollständig IN der Schrift: helle Glut oben, tiefes Orange unten.
        fill_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = fill_layer.load()
        top, bottom = bbox[1], max(bbox[3], bbox[1] + 1)
        for py in range(top, bottom):
            t = (py - top) / (bottom - top)
            if subtitle:
                color = (255, int(186 - 65*t), int(65 - 42*t), 255)
            elif t < 0.40:
                f = t / 0.40
                color = (255, int(179 - 83*f), int(35 - 28*f), 255)
            else:
                f = (t - 0.40) / 0.60
                color = (int(255 - 28*f), int(96 - 57*f), int(7 - 7*f), 255)
            for px in range(bbox[0], bbox[2]):
                pixels[px, py] = color
        fill_layer.putalpha(mask)
        base.alpha_composite(fill_layer)

        if not subtitle:
            # Schwarze, unregelmäßige Brandadern, ausschließlich in den Glyphen.
            rng = random.Random(seed)
            crack_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            cracks = ImageDraw.Draw(crack_layer)
            for _ in range(35):
                cx = rng.randint(bbox[0], bbox[2] - 1)
                cy = rng.randint(bbox[1], bbox[3] - 1)
                length = rng.randint(7, 24)
                points = [(cx, cy)]
                for step in range(3):
                    cx += rng.randint(-7, 7)
                    cy += max(1, length // 3) + rng.randint(-2, 2)
                    points.append((cx, cy))
                cracks.line(points, fill=(22, 5, 3, rng.randint(145, 215)), width=rng.choice((1, 2, 2, 3)))
            crack_alpha = Image.composite(crack_layer.getchannel("A"),
                                          Image.new("L", (width, height), 0), mask)
            crack_layer.putalpha(crack_alpha)
            base.alpha_composite(crack_layer)

    ember_text(title, title_font, top_y, seed=20261014, spacing=title_spacing)
    ember_text(subtitle, subtitle_font, top_y + title_height + gap,
               seed=20261104, subtitle=True)
    result = io.BytesIO()
    base.convert("RGB").save(result, format="PNG", optimize=True)
    return result.getvalue()


def entry_line(entry):
    """Einheitliche, kompakte Zeilen mit klar erkennbarer Belohnung."""
    if "days" in entry:
        return f'• **Tag {entry["days"]}**  —  **{entry["coins_per_day"]} Münzen/Tag**'
    name = entry.get("name", "")
    if "task" in entry:
        return f'• {name}: {entry["task"]}  →  **{entry["coins"]} Münzen**'
    if "price" in entry:
        return f'• **{name}**  —  **{entry["price"]} Münzen**\n  ↳ {entry["limit"]} · ab Stufe {entry["level"]}'
    if "fragments" in entry:
        return f'• {name} ×{entry["quantity"]}  —  **{entry["fragments"]} Fragmente**'
    if "effects" in entry:
        effects = " · ".join(entry["effects"])
        return f'• **{name}** ({entry["duration"]})\n  ↳ {effects}'
    qty = f'{entry.get("quantity", 1):,}'.replace(",", ".")
    return f'• {name}  —  **×{qty}**'


def detail_embeds():
    """Neun übersichtliche Abschnitte; die Daten bleiben unverändert."""
    embeds = []
    for section in EVENT["sections"]:
        lines = []
        if section.get("description"):
            lines.extend((section["description"], ""))
        lines.extend(entry_line(entry) for entry in section["entries"])
        description = "\n".join(lines)
        if len(description) > 4096:
            raise ValueError(f'Eventabschnitt zu lang: {section["title"]}')
        embeds.append({
            "title": section["title"],
            "description": description,
            "color": 0xFF7100,
        })
    return embeds


def payload(current):
    """Großes Banner als Anhang, Quellen-Embed und Details nur während des Events."""
    source = EVENT["source_url"]
    if not source.startswith("https://"):
        raise ValueError("Gültige HTTPS-Quellen-URL fehlt")
    link = {
        "title": "🔗 Eventankündigung & Belohnungen ansehen",
        "url": source,
        "description": "Patchnotes und ursprüngliche Belohnungstabellen öffnen ↗",
        "color": 0xFF7100,
    }
    embeds = [link] + (detail_embeds() if current == "active" else [])
    if len(embeds) > 10:
        raise ValueError("Discord erlaubt maximal 10 Embeds")
    if sum(len(e.get("title", "")) + len(e.get("description", "")) for e in embeds) > 6000:
        raise ValueError("Discord erlaubt maximal 6000 Zeichen in allen Embeds")
    return {"embeds": embeds, "components": [], "allowed_mentions": {"parse": []}}
