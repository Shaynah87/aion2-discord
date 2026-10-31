
"""Nyerk24 · Anwesenheitslisten.

Kategoriedaten und Discord-Buttondefinitionen.
Interaktionen verarbeitet der bestehende Nyerk24 Helper.
Zeitraeume gegen offizielle Ankuendigungen pruefen.
"""

CATEGORY_ID = "anwesenheitslisten"
CATEGORY_TITLE = "Anwesenheitslisten"
BANNER = "Anwesenheit/anwesenheitslisten.png"

EVENTS = (
    {
        "id": "atreias_ruf",
        "name": "Atreias Ruf",
        "start": "2026-10-28",
        "end": "2026-12-02",
        "date_label": "28.10.–02.12.26",
        "custom_id": "event:details:atreias_ruf",
    },
    {
        "id": "taegliche_anwesenheit",
        "name": "Tägliche Anwesenheitsliste",
        "start": "2026-09-30",
        "end": "2026-12-16",
        "date_label": "30.09.–16.12.26",
        "custom_id": "event:details:taegliche_anwesenheit",
    },
    {
        "id": "shugo_anwesenheit",
        "name": "Shugo-Anwesenheitsliste",
        "start": "2026-09-30",
        "end": "2026-12-16",
        "date_label": "30.09.–16.12.26",
        "custom_id": "event:details:shugo_anwesenheit",
    },
    {
        "id": "suesses_oder_saures",
        "name": "Süßes oder Saures",
        "start": "2026-10-14",
        "end": "2026-11-04",
        "date_label": "14.10.–04.11.26",
        "custom_id": "event:details:suesses_oder_saures",
    },
)


def buttons():
    """Discord-Action-Row mit vier Buttons (API v10)."""
    return [{
        "type": 1,
        "components": [
            {
                "type": 2,
                "style": 2,
                "label": (
                    f'{event["name"]} · '
                    f'{event["date_label"]}'
                ),
                "custom_id": event["custom_id"],
            }
            for event in EVENTS
        ],
    }]


def get_event(custom_id):
    """Event anhand der Discord-ID finden."""
    return next(
        (
            event
            for event in EVENTS
            if event["custom_id"] == custom_id
        ),
        None,
    )


if __name__ == "__main__":
    for event in EVENTS:
        print(
            f'{event["name"]}: '
            f'{event["date_label"]} '
            f'[{event["custom_id"]}]'
        )
