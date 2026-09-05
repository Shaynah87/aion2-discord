import os
import requests

WEBHOOK_URL = os.environ["EVENTS_WEBHOOK_URL"] "https://raw.githubusercontent.com/Shaynah87/aion2-discord/main/Events/coming_soon_e.png"

payload = {
    "username": "Nyerk24 · Events",
    "embeds": [
        {
            "image": {
                "url": IMAGE_URL
            }
        }
    ]
}

response = requests.post(WEBHOOK_URL, json=payload)

if response.status_code in (200, 204):
    print("Coming Soon · Events wurde erfolgreich gepostet.")
else:
    print("Fehler:", response.status_code)
    print(response.text)
