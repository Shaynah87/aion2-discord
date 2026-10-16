
        {
"""Halloween 2026 – feste Eventdaten für den Discord-Eventkanal.

Keine externen Datenquellen. Zeiten werden in Europe/Berlin interpretiert.
Das Event endet am 04.11.2026 um 09:00 Uhr MEZ.
"""
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
            "description": "Im Spiel unter [Saisonmission] > [Event]. Die Missionen werden wöchentlich zurückgesetzt. Belohnungen jeweils in Halloween-Kürbismünzen (Event).",
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
            "description": "Beim Event-Münzhändler in den Städten. Preise in Halloween-Kürbismünzen (Event); Menge je Kauf: 1.",
            "entries": [
                {"name": "Halloween-Spezialtruhe", "price": 250, "limit": "1 pro Server"},
                {"name": "Odenergie (Gebunden)", "price": 10, "limit": "4 pro Server/Woche"},
                {"name": "Abyss-Rissstein: Untere Ebene (Gebunden)", "price": 30, "limit": "2 pro Server/Woche"},
                {"name": "Skin-Truhe (10x) (Gebunden)", "price": 15, "limit": "5 pro Server/Woche"},
                {"name": "Geiststein der Wiederbelebung (Gebunden)", "price": 2, "limit": "10 pro Server/Woche"},
                {"name": "Sofortabschluss-Ticket: Täglicher Dungeon (Gebunden)", "price": 3, "limit": "7 pro Server/Woche"},
                {"name": "Herausforderungsticket: Albtraum-Dungeon (Gebunden)", "price": 7, "limit": "3 pro Server/Woche"},
                {"name": "Shugofesta-Schlüssel (Gebunden)", "price": 7, "limit": "3 pro Server/Woche"},
                {"name": "Lebenskristall (Gebunden)", "price": 2, "limit": "20 pro Charakter"},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "price": 2, "limit": "10 pro Charakter"},
                {"name": "Halloween-Keks (Gebunden)", "price": 2, "limit": "10 pro Charakter"},
                {"name": "Hochwertiger Siegelstein (Gebunden)", "price": 1, "limit": "Keine angegebene Begrenzung"},
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
            "description": "Süßigkeitenschlüssel-Fragmente (Event) erhältst du bei Expeditions- und Transzendenz-Zusammenstößen. Erfolgsrate aller Umwandlungen: 100 %. Ein mögliches Kauflimit der Schlüssel war in der Vorlage nicht vollständig lesbar.",
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
