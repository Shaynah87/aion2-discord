# Events/Anwesenheit/anwesenheitslisten.py
# Eventdaten der Anwesenheitslisten; das Banner und die Schriftgestaltung
# werden ausschließlich von Events/events.py verarbeitet.

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
    {
        "id": "ludra_anwesenheit",
        "name": "Ludra-Eroberung",
        "start": "2026-11-04T15:00:00+01:00",
        "end": "2026-11-18T09:00:00+01:00",
        "date_label": "04.11.–18.11.26",
        "custom_id": "event:details:ludra_anwesenheit",
    },
)


def buttons():
    return [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "label": f'{event["name"]} · {event["date_label"]}',
                    "custom_id": event["custom_id"],
                }
                for event in EVENTS
            ],
        }
    ]


def get_event(custom_id):
    return next(
        (event for event in EVENTS if event["custom_id"] == custom_id),
        None,
    )
